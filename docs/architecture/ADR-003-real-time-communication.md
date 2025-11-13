# ADR-003: Real-Time Communication for Scan Progress

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Real-time progress updates for security scans

## Context and Problem Statement

Security scans can take minutes to hours depending on codebase size. Users need real-time feedback about scan progress, not just "pending" and "completed" states. We need to decide how to push progress updates from background workers to the frontend.

Three primary approaches exist:
1. **WebSockets:** Bidirectional, persistent connection
2. **Server-Sent Events (SSE):** Unidirectional, server-to-client streaming over HTTP
3. **Polling:** Client periodically requests status via REST API

The decision impacts infrastructure complexity, scalability, developer experience, and compatibility with enterprise networks.

## Decision Drivers

- **Use case:** Unidirectional updates (server → client) for progress bars, logs, status
- **Infrastructure simplicity:** Minimize operational complexity (load balancers, proxies)
- **Developer experience:** Easy to implement and debug
- **Scalability:** Handle thousands of concurrent scans
- **Network compatibility:** Work through corporate firewalls and proxies
- **Reconnection:** Graceful handling of network interruptions
- **Fallback:** Degraded experience if real-time is blocked

## Considered Options

### Option 1: WebSockets

Establish bidirectional, persistent TCP connection using WebSocket protocol.

**Technology:** Django Channels with Redis backend, Socket.IO (Node.js alternative)

```python
# Example with Django Channels
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ScanProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scan_id = self.scope['url_route']['kwargs']['scan_id']
        await self.channel_layer.group_add(f"scan_{self.scan_id}", self.channel_name)
        await self.accept()

    async def scan_progress(self, event):
        await self.send(text_data=json.dumps(event['data']))
```

**Pros:**
- True bidirectional communication
- Low latency (persistent connection)
- Can send structured messages (JSON)
- Wide browser support

**Cons:**
- Requires WebSocket-aware load balancers (sticky sessions or routing)
- More complex infrastructure (ASGI servers like Daphne, Uvicorn)
- Protocol upgrade complexity (HTTP → WS)
- Some corporate firewalls block WebSocket traffic
- Overkill for unidirectional progress updates
- Harder to debug (not standard HTTP)

### Option 2: Server-Sent Events (SSE)

Use HTTP streaming with `text/event-stream` content type for server → client updates.

**Technology:** Django async views, FastAPI endpoints

```python
# Django async view with SSE
import asyncio
import json
from django.http import StreamingHttpResponse
from redis import asyncio as aioredis

async def scan_progress(request, scan_id):
    redis = await aioredis.from_url('redis://localhost')
    pubsub = redis.pubsub()
    await pubsub.subscribe(f'scan:{scan_id}:progress')

    async def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'status': 'connected'})}\n\n"

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await redis.close()

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response
```

**Pros:**
- Built on standard HTTP (no protocol upgrade)
- Works through most proxies and firewalls
- Auto-reconnect built into browser EventSource API
- Simpler infrastructure (standard HTTP load balancing)
- Perfect for unidirectional updates (server → client)
- Easy to debug (inspect in browser network tab)
- Native browser API (`EventSource`)

**Cons:**
- Unidirectional only (can't send from client easily)
- HTTP/1.1 connection limits (6 per domain, but HTTP/2 fixes this)
- Less common than WebSockets (but growing adoption)
- Not supported in Internet Explorer (Edge is fine)

### Option 3: Short Polling

Client requests status endpoint every N seconds (e.g., every 2 seconds).

```python
# REST endpoint
@api_view(['GET'])
def scan_status(request, scan_id):
    scan = Scan.objects.get(id=scan_id, org_id=request.user.org_id)
    return Response({
        'status': scan.status,
        'progress': scan.progress_percentage,
        'current_step': scan.current_step,
        'findings_count': scan.findings_count,
    })
```

```javascript
// Client polling
async function pollScanStatus(scanId) {
    const interval = setInterval(async () => {
        const response = await fetch(`/api/scans/${scanId}/status`);
        const data = await response.json();

        updateUI(data);

        if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(interval);
        }
    }, 2000);
}
```

**Pros:**
- Simple to implement (standard REST API)
- No special infrastructure required
- Works everywhere (no protocol restrictions)
- Stateless (no connection management)
- Easy to debug

**Cons:**
- Inefficient (constant requests even when no updates)
- Higher latency (up to polling interval)
- Increased server load (N clients × polling frequency)
- Wastes bandwidth (many "no change" responses)
- Battery drain on mobile devices

### Option 4: Long Polling

Client requests status, server holds connection open until update available.

**Pros:**
- Lower latency than short polling
- Works through firewalls
- No special protocol

**Cons:**
- Complex to implement correctly
- Server must manage many hanging connections
- SSE is strictly better (designed for this use case)

## Decision Outcome

**Chosen option:** Option 2 - Server-Sent Events (SSE) with short polling fallback.

### Justification

1. **Perfect fit for use case:** Scan progress is inherently unidirectional (server → client)
2. **Simpler infrastructure than WebSockets:** Standard HTTP, no special load balancer config
3. **Better than polling:** Lower latency, less bandwidth, lower server load
4. **Broad compatibility:** Works through most corporate proxies
5. **Native browser support:** `EventSource` API is simple and reliable
6. **Easy debugging:** SSE traffic visible in browser network tab

**Fallback strategy:** If SSE is blocked (rare), client can fall back to short polling (every 3-5 seconds).

### Implementation Strategy

#### 1. Backend: Django Async View with Redis Pub/Sub

```python
# views/scan_progress.py
import asyncio
import json
from django.http import StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from redis import asyncio as aioredis
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
async def scan_progress_stream(request, scan_id):
    """
    SSE endpoint for real-time scan progress updates.
    """
    # Verify user has access to this scan
    org_id = request.user.org_id
    try:
        scan = await Scan.objects.select_related('project').aget(
            id=scan_id,
            project__org_id=org_id
        )
    except Scan.DoesNotExist:
        return JsonResponse({'error': 'Scan not found'}, status=404)

    # Connect to Redis for pub/sub
    redis = await aioredis.from_url(settings.REDIS_URL)
    pubsub = redis.pubsub()
    channel = f'scan:{scan_id}:progress'
    await pubsub.subscribe(channel)

    async def event_stream():
        """
        Generate SSE events from Redis pub/sub.
        """
        # Send initial state
        initial_data = {
            'status': scan.status,
            'progress': scan.progress_percentage,
            'step': scan.current_step,
        }
        yield f"data: {json.dumps(initial_data)}\n\n"

        try:
            # Keep connection alive with heartbeat
            heartbeat_task = asyncio.create_task(send_heartbeat())

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield f"data: {json.dumps(data)}\n\n"

                        # Close stream if scan is terminal state
                        if data.get('status') in ['completed', 'failed', 'cancelled']:
                            break
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in Redis message: {message['data']}")

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for scan {scan_id}")
        finally:
            heartbeat_task.cancel()
            await pubsub.unsubscribe(channel)
            await redis.close()

    async def send_heartbeat():
        """Send periodic comments to keep connection alive."""
        while True:
            await asyncio.sleep(15)
            yield ": heartbeat\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    response['Connection'] = 'keep-alive'
    return response
```

#### 2. Worker: Publish Progress to Redis

```python
# workers/scan_worker.py
from celery import shared_task
from redis import Redis
import json

@shared_task
def run_security_scan(scan_id):
    redis = Redis.from_url(settings.REDIS_URL)
    channel = f'scan:{scan_id}:progress'

    def publish_progress(status, progress, step, findings_count=0):
        data = {
            'status': status,
            'progress': progress,
            'step': step,
            'findings_count': findings_count,
            'timestamp': timezone.now().isoformat(),
        }
        redis.publish(channel, json.dumps(data))

    try:
        publish_progress('running', 0, 'Cloning repository')
        repo = clone_repository(scan_id)

        publish_progress('running', 25, 'Running static analysis')
        findings = run_static_analysis(repo)

        publish_progress('running', 50, 'Running dependency scan')
        findings += run_dependency_scan(repo)

        publish_progress('running', 75, 'Generating SARIF report')
        sarif = generate_sarif(findings)

        publish_progress('running', 90, 'Saving results')
        save_findings(scan_id, findings, sarif)

        publish_progress('completed', 100, 'Scan complete', len(findings))

    except Exception as e:
        publish_progress('failed', 0, f'Error: {str(e)}')
        raise
```

#### 3. Frontend: EventSource Client with Fallback

```javascript
// services/scanProgressService.js
class ScanProgressService {
    constructor(scanId) {
        this.scanId = scanId;
        this.eventSource = null;
        this.pollingInterval = null;
        this.onProgress = null;
        this.useSSE = true;
    }

    start(onProgress) {
        this.onProgress = onProgress;

        // Try SSE first
        if (this.useSSE && typeof EventSource !== 'undefined') {
            this.startSSE();
        } else {
            this.startPolling();
        }
    }

    startSSE() {
        this.eventSource = new EventSource(`/api/scans/${this.scanId}/progress`);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.onProgress(data);

            if (data.status === 'completed' || data.status === 'failed') {
                this.stop();
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE error, falling back to polling', error);
            this.stop();
            this.useSSE = false;
            this.startPolling();
        };
    }

    startPolling() {
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/scans/${this.scanId}/status`);
                const data = await response.json();
                this.onProgress(data);

                if (data.status === 'completed' || data.status === 'failed') {
                    this.stop();
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 3000); // Poll every 3 seconds
    }

    stop() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

// Usage in React component
function ScanProgressView({ scanId }) {
    const [progress, setProgress] = useState({ status: 'pending', progress: 0 });

    useEffect(() => {
        const service = new ScanProgressService(scanId);
        service.start((data) => setProgress(data));

        return () => service.stop();
    }, [scanId]);

    return (
        <div>
            <ProgressBar value={progress.progress} />
            <p>{progress.step}</p>
            <p>Status: {progress.status}</p>
        </div>
    );
}
```

#### 4. Infrastructure: Nginx Configuration

```nginx
# nginx.conf - SSE-specific settings
location /api/scans/ {
    proxy_pass http://django_backend;
    proxy_http_version 1.1;

    # Essential for SSE
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;

    # Timeouts for long-lived connections
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

### Scalability Considerations

**Redis Pub/Sub scaling:**
- Each scan has its own channel (`scan:{scan_id}:progress`)
- Redis can handle millions of channels
- For extreme scale, shard by `scan_id % N` across Redis instances

**Connection limits:**
- Each SSE connection holds 1 backend connection
- Use async Django (Uvicorn/Daphne) for efficient connection handling
- 1 server can handle 10,000+ concurrent SSE connections with async

**Deployment:**
- Deploy Django with ASGI server (Uvicorn, Daphne, Hypercorn)
- Use Redis for pub/sub (existing Redis instance is fine)
- No special load balancer config needed (unlike WebSockets)

## Consequences

### Positive

- **Simple infrastructure:** No WebSocket-specific load balancer config
- **Good developer experience:** Easy to implement and debug
- **Network compatible:** Works through most firewalls and proxies
- **Efficient:** Lower latency and bandwidth than polling
- **Auto-reconnect:** Browser handles reconnection automatically
- **Fallback available:** Can gracefully degrade to polling

### Negative

- **Unidirectional only:** Can't easily send from client (not needed for this use case)
- **HTTP/1.1 connection limits:** Max 6 SSE streams per domain (HTTP/2 removes limit)
- **No IE support:** Internet Explorer doesn't support EventSource (Edge is fine)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Corporate firewall blocks SSE | Fallback to short polling (3-5 second interval) |
| HTTP/1.1 connection limit (6 per domain) | Use HTTP/2; use subdomain for SSE (sse.example.com) |
| Connection drops without notification | Heartbeat comments every 15s; client timeout detection |
| Server memory leak from abandoned connections | Connection timeout (1 hour); monitor connection count |

## Related Decisions

- **ADR-004:** Worker security model (workers publish progress to Redis)
- **ADR-008:** Rate limiting (limit concurrent SSE connections per org)

## References

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [EventSource Browser API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [Django Async Views](https://docs.djangoproject.com/en/stable/topics/async/)
- [SSE vs WebSockets](https://ably.com/topic/server-sent-events-vs-websockets)
- [Redis Pub/Sub](https://redis.io/topics/pubsub)
