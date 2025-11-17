"""
Server-Sent Events (SSE) for real-time scan updates (ADR-003).

Provides real-time streaming of scan status updates, finding discoveries,
and progress information to connected clients.
"""
import json
import logging
import time
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.organizations.permissions import IsOrganizationMember
from apps.scans.models import Scan
import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class ScanEventStream(View):
    """
    SSE endpoint for real-time scan updates.

    Streams events via Server-Sent Events protocol:
    - Scan status changes (pending -> queued -> running -> completed/failed)
    - Finding discoveries
    - Progress updates
    - Log messages
    """

    def get(self, request, scan_id):
        """
        Stream scan events to client.

        Args:
            scan_id: UUID of the scan to monitor

        Returns:
            StreamingHttpResponse with text/event-stream content type
        """
        # Verify user has access to this scan
        try:
            scan = Scan.objects.select_related(
                'organization', 'repository'
            ).get(id=scan_id)

            # Check if user is member of the organization
            user = request.user
            if not user.is_superuser:
                if not user.organization_memberships.filter(
                    organization=scan.organization
                ).exists():
                    logger.warning(
                        f"User {user.email} attempted to access scan {scan_id} "
                        f"without permission"
                    )
                    return StreamingHttpResponse(
                        _error_event('Forbidden: You do not have access to this scan'),
                        content_type='text/event-stream',
                        status=403
                    )
        except Scan.DoesNotExist:
            return StreamingHttpResponse(
                _error_event('Scan not found'),
                content_type='text/event-stream',
                status=404
            )

        # Create event generator
        response = StreamingHttpResponse(
            self.event_generator(scan_id, scan),
            content_type='text/event-stream'
        )

        # SSE headers
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering

        return response

    def event_generator(self, scan_id, scan):
        """
        Generate SSE events for scan.

        Subscribes to Redis pub/sub channel for real-time updates.
        Sends heartbeat every 15 seconds to keep connection alive.

        Yields:
            SSE formatted event strings
        """
        try:
            # Connect to Redis
            redis_client = redis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()

            # Subscribe to scan-specific channel
            channel = f'scan:{scan_id}:events'
            pubsub.subscribe(channel)

            logger.info(f"SSE client connected for scan {scan_id}")

            # Send initial connection event
            yield _format_event('connected', {
                'scan_id': str(scan_id),
                'status': scan.status,
                'message': 'Connected to scan event stream'
            })

            # Send current scan state
            yield _format_event('status', {
                'scan_id': str(scan_id),
                'status': scan.status,
                'findings_count': scan.findings_count or 0
            })

            # Listen for events with timeout
            last_heartbeat = time.time()
            heartbeat_interval = 15  # seconds

            for message in pubsub.listen():
                # Check if we should send heartbeat
                now = time.time()
                if now - last_heartbeat >= heartbeat_interval:
                    yield _format_event('heartbeat', {'timestamp': int(now)})
                    last_heartbeat = now

                # Process message
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event_type = event_data.get('type', 'update')

                        # Format and send event
                        yield _format_event(event_type, event_data)

                        # If scan completed or failed, close stream
                        if event_type in ['completed', 'failed']:
                            logger.info(f"Scan {scan_id} finished, closing SSE stream")
                            break

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in Redis message: {e}")
                        continue

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            yield _format_event('error', {
                'message': 'Lost connection to event stream'
            })

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield _format_event('error', {
                'message': 'Internal server error'
            })

        finally:
            # Cleanup
            try:
                pubsub.unsubscribe()
                pubsub.close()
                logger.info(f"SSE client disconnected for scan {scan_id}")
            except:
                pass


def _format_event(event_type, data):
    """
    Format data as SSE event.

    SSE format:
    event: <event_type>
    data: <json_data>

    Args:
        event_type: Type of event (status, finding, log, etc.)
        data: Event data dictionary

    Returns:
        Formatted SSE string
    """
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def _error_event(message):
    """Generate error event generator."""
    yield _format_event('error', {'message': message})


# REST API view for SSE endpoint (authentication wrapper)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scan_events_view(request, scan_id):
    """
    API endpoint for scan event stream.

    Usage:
        GET /api/v1/scans/{scan_id}/events/

    Returns:
        StreamingResponse with SSE events
    """
    view = ScanEventStream.as_view()
    return view(request, scan_id=scan_id)


# Polling fallback endpoint (for clients that don't support SSE)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOrganizationMember])
def scan_status_view(request, scan_id):
    """
    Polling endpoint for scan status (fallback for SSE).

    Returns current scan state including:
    - Status
    - Progress
    - Findings count
    - Recent logs

    Args:
        scan_id: UUID of scan

    Returns:
        JSON response with current scan state
    """
    try:
        scan = Scan.objects.select_related(
            'organization', 'repository', 'branch'
        ).get(id=scan_id)

        # Get recent logs (last 10)
        recent_logs = scan.logs.order_by('-created_at')[:10]

        return Response({
            'scan_id': str(scan.id),
            'status': scan.status,
            'findings_count': scan.findings_count or 0,
            'started_at': scan.started_at.isoformat() if scan.started_at else None,
            'completed_at': scan.completed_at.isoformat() if scan.completed_at else None,
            'error_message': scan.error_message,
            'recent_logs': [
                {
                    'level': log.level,
                    'message': log.message,
                    'timestamp': log.created_at.isoformat()
                }
                for log in recent_logs
            ]
        })

    except Scan.DoesNotExist:
        return Response(
            {'error': 'Scan not found'},
            status=404
        )
