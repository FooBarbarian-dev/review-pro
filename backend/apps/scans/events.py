"""
Event publishing utilities for real-time scan updates via Redis pub/sub.

These functions are called from the scan worker to publish events
to connected SSE clients.
"""
import json
import logging
import redis
from django.conf import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ScanEventPublisher:
    """
    Publish scan events to Redis pub/sub for SSE streaming.
    """

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def publish_event(
        self,
        scan_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Publish event to Redis channel.

        Args:
            scan_id: UUID of the scan
            event_type: Type of event (status, finding, log, progress)
            data: Event data dictionary

        Returns:
            True if published successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not available, cannot publish event")
            return False

        try:
            channel = f'scan:{scan_id}:events'

            # Add event type to data
            event_data = {
                'type': event_type,
                'scan_id': scan_id,
                **data
            }

            # Publish to Redis
            message = json.dumps(event_data)
            subscribers = self.redis_client.publish(channel, message)

            if subscribers > 0:
                logger.debug(
                    f"Published {event_type} event for scan {scan_id} "
                    f"to {subscribers} subscribers"
                )
            else:
                logger.debug(
                    f"Published {event_type} event for scan {scan_id} "
                    f"(no active subscribers)"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def publish_status_change(
        self,
        scan_id: str,
        status: str,
        message: Optional[str] = None
    ):
        """
        Publish scan status change event.

        Args:
            scan_id: UUID of the scan
            status: New status (queued, running, completed, failed)
            message: Optional status message
        """
        data = {'status': status}
        if message:
            data['message'] = message

        self.publish_event(scan_id, 'status', data)

    def publish_finding_discovered(
        self,
        scan_id: str,
        finding_id: str,
        severity: str,
        rule_id: str,
        file_path: str
    ):
        """
        Publish finding discovery event.

        Args:
            scan_id: UUID of the scan
            finding_id: UUID of the finding
            severity: Finding severity (critical, high, medium, low)
            rule_id: Security rule ID
            file_path: File where finding was detected
        """
        data = {
            'finding_id': finding_id,
            'severity': severity,
            'rule_id': rule_id,
            'file_path': file_path
        }

        self.publish_event(scan_id, 'finding', data)

    def publish_progress(
        self,
        scan_id: str,
        stage: str,
        progress: int,
        total: Optional[int] = None,
        message: Optional[str] = None
    ):
        """
        Publish scan progress event.

        Args:
            scan_id: UUID of the scan
            stage: Current stage (cloning, scanning, parsing, etc.)
            progress: Current progress (items processed)
            total: Total items (optional)
            message: Optional progress message
        """
        data = {
            'stage': stage,
            'progress': progress
        }

        if total is not None:
            data['total'] = total
            data['percentage'] = int((progress / total) * 100) if total > 0 else 0

        if message:
            data['message'] = message

        self.publish_event(scan_id, 'progress', data)

    def publish_log(
        self,
        scan_id: str,
        level: str,
        message: str
    ):
        """
        Publish scan log event.

        Args:
            scan_id: UUID of the scan
            level: Log level (info, warning, error, success)
            message: Log message
        """
        data = {
            'level': level,
            'message': message
        }

        self.publish_event(scan_id, 'log', data)

    def publish_scan_completed(
        self,
        scan_id: str,
        findings_count: int,
        duration_seconds: float
    ):
        """
        Publish scan completion event.

        Args:
            scan_id: UUID of the scan
            findings_count: Total findings discovered
            duration_seconds: Scan duration in seconds
        """
        data = {
            'findings_count': findings_count,
            'duration_seconds': round(duration_seconds, 2)
        }

        self.publish_event(scan_id, 'completed', data)

    def publish_scan_failed(
        self,
        scan_id: str,
        error_message: str
    ):
        """
        Publish scan failure event.

        Args:
            scan_id: UUID of the scan
            error_message: Error description
        """
        data = {
            'error_message': error_message
        }

        self.publish_event(scan_id, 'failed', data)


# Singleton instance
_publisher_instance = None


def get_event_publisher() -> ScanEventPublisher:
    """
    Get singleton ScanEventPublisher instance.

    Returns:
        ScanEventPublisher instance
    """
    global _publisher_instance

    if _publisher_instance is None:
        _publisher_instance = ScanEventPublisher()

    return _publisher_instance


# Convenience functions for common events
def publish_status_change(scan_id: str, status: str, message: str = None):
    """Publish status change event."""
    publisher = get_event_publisher()
    publisher.publish_status_change(scan_id, status, message)


def publish_finding_discovered(
    scan_id: str,
    finding_id: str,
    severity: str,
    rule_id: str,
    file_path: str
):
    """Publish finding discovery event."""
    publisher = get_event_publisher()
    publisher.publish_finding_discovered(
        scan_id, finding_id, severity, rule_id, file_path
    )


def publish_progress(
    scan_id: str,
    stage: str,
    progress: int,
    total: int = None,
    message: str = None
):
    """Publish progress event."""
    publisher = get_event_publisher()
    publisher.publish_progress(scan_id, stage, progress, total, message)


def publish_log(scan_id: str, level: str, message: str):
    """Publish log event."""
    publisher = get_event_publisher()
    publisher.publish_log(scan_id, level, message)


def publish_scan_completed(scan_id: str, findings_count: int, duration_seconds: float):
    """Publish scan completion event."""
    publisher = get_event_publisher()
    publisher.publish_scan_completed(scan_id, findings_count, duration_seconds)


def publish_scan_failed(scan_id: str, error_message: str):
    """Publish scan failure event."""
    publisher = get_event_publisher()
    publisher.publish_scan_failed(scan_id, error_message)
