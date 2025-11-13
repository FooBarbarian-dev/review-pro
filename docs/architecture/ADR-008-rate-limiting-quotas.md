# ADR-008: Rate Limiting & Quotas

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Resource limits and abuse prevention

## Context and Problem Statement

Our security analysis platform consumes significant compute resources (scans) and storage (SARIF files, findings). Without limits, we face:

1. **Abuse:** Malicious users could overwhelm our infrastructure
2. **Cost overruns:** Unlimited scans = unlimited costs
3. **Resource starvation:** Heavy users could impact others
4. **Poor user experience:** No feedback on usage limits

We need to implement:
- **Rate limiting:** Limit request frequency (API calls per minute)
- **Quotas:** Limit resource consumption (scans per month, storage per org)
- **Concurrency limits:** Limit simultaneous operations (concurrent scans)

## Decision Drivers

- **Prevent abuse:** Protect infrastructure from malicious or accidental overuse
- **Fair resource allocation:** Ensure all users get reasonable access
- **Cost control:** Prevent runaway infrastructure costs
- **User experience:** Clear, informative error messages when limits hit
- **Flexibility:** Different limits for different pricing tiers

## Considered Options

### Option 1: Application-Level Rate Limiting (In-Memory)

Use in-memory counters in Django process.

**Pros:**
- Simple to implement
- No external dependencies

**Cons:**
- ❌ Not shared across multiple servers (each server has own limit)
- ❌ Lost on server restart
- ❌ Can't enforce global limits

### Option 2: Redis-Based Rate Limiting

Use Redis with sliding window or token bucket algorithm.

**Pros:**
- ✅ Shared across all servers
- ✅ Persists across restarts
- ✅ Atomic operations (thread-safe)
- ✅ Fast (in-memory)
- ✅ Built-in TTL for automatic cleanup

**Cons:**
- Requires Redis infrastructure (we already have for SSE)

### Option 3: Database-Based Quotas

Store quota usage in PostgreSQL.

**Pros:**
- ✅ Persistent and durable
- ✅ ACID guarantees
- ✅ Can query usage history

**Cons:**
- Slower than Redis (disk I/O)
- Can become bottleneck under high load
- Requires locks for atomic increments

### Option 4: Hybrid (Redis for Rate Limits, Database for Quotas)

Use Redis for short-term rate limits, PostgreSQL for long-term quotas.

**Pros:**
- ✅ Best of both worlds
- ✅ Fast rate limiting
- ✅ Durable quota tracking
- ✅ Separate concerns (ephemeral vs persistent)

**Cons:**
- More complex (two systems to manage)

## Decision Outcome

**Chosen option:** Option 4 - Hybrid approach (Redis for rate limits, PostgreSQL for quotas).

### Justification

1. **Redis for rate limits:** Fast, atomic, shared across servers, automatic TTL
2. **PostgreSQL for quotas:** Durable, queryable, supports billing integration
3. **Separation of concerns:** Rate limits are ephemeral (per minute/hour), quotas are monthly/annual
4. **We already have Redis:** Used for SSE pub/sub (ADR-003)

### Implementation Strategy

#### 1. Rate Limiting Tiers

```python
# Rate limit tiers
RATE_LIMITS = {
    'free': {
        'api_calls': 60,       # 60 requests per minute
        'scans': 10,           # 10 scans per hour
    },
    'pro': {
        'api_calls': 600,      # 600 requests per minute
        'scans': 100,          # 100 scans per hour
    },
    'enterprise': {
        'api_calls': 6000,     # 6000 requests per minute
        'scans': 1000,         # 1000 scans per hour
    },
}
```

#### 2. Redis Rate Limiter (Token Bucket Algorithm)

```python
# services/rate_limiter.py
from redis import Redis
from django.conf import settings
import time

class RateLimiter:
    """
    Token bucket rate limiter using Redis.
    """

    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL)

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> dict:
        """
        Check if request is within rate limit using sliding window.

        Args:
            key: Rate limit key (e.g., "api:org_123", "scans:org_456")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            {
                'allowed': bool,
                'remaining': int,
                'reset_at': int (unix timestamp)
            }
        """
        now = time.time()
        window_key = f"ratelimit:{key}"

        # Use sliding window with sorted set
        pipe = self.redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(window_key, 0, now - window_seconds)

        # Count requests in current window
        pipe.zcard(window_key)

        # Add current request timestamp
        pipe.zadd(window_key, {str(now): now})

        # Set expiry on key
        pipe.expire(window_key, window_seconds)

        results = pipe.execute()
        current_count = results[1]

        if current_count < max_requests:
            return {
                'allowed': True,
                'remaining': max_requests - current_count - 1,
                'reset_at': int(now + window_seconds)
            }
        else:
            # Get oldest timestamp in window
            oldest = self.redis.zrange(window_key, 0, 0, withscores=True)
            if oldest:
                reset_at = int(oldest[0][1] + window_seconds)
            else:
                reset_at = int(now + window_seconds)

            return {
                'allowed': False,
                'remaining': 0,
                'reset_at': reset_at
            }

# Usage
rate_limiter = RateLimiter()

# API rate limit (60 requests per minute)
result = rate_limiter.check_rate_limit(
    key=f"api:{org_id}",
    max_requests=60,
    window_seconds=60
)

if not result['allowed']:
    raise RateLimitExceeded(
        f"Rate limit exceeded. Try again in {result['reset_at'] - time.time():.0f} seconds"
    )
```

#### 3. Rate Limiting Middleware

```python
# middleware/rate_limit.py
from django.http import JsonResponse
from services.rate_limiter import RateLimiter
import time

class RateLimitMiddleware:
    """
    Global API rate limiting middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limiter = RateLimiter()

    def __call__(self, request):
        # Skip rate limiting for unauthenticated requests (handled by auth)
        if not hasattr(request, 'org_id') or not request.org_id:
            return self.get_response(request)

        # Get org's rate limit tier
        org = Organization.objects.get(id=request.org_id)
        tier = org.subscription_tier  # 'free', 'pro', 'enterprise'
        limits = RATE_LIMITS.get(tier, RATE_LIMITS['free'])

        # Check API rate limit
        result = self.rate_limiter.check_rate_limit(
            key=f"api:{request.org_id}",
            max_requests=limits['api_calls'],
            window_seconds=60  # per minute
        )

        # Add rate limit headers
        response = self.get_response(request)
        response['X-RateLimit-Limit'] = limits['api_calls']
        response['X-RateLimit-Remaining'] = result['remaining']
        response['X-RateLimit-Reset'] = result['reset_at']

        if not result['allowed']:
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': f"You have exceeded the rate limit of {limits['api_calls']} requests per minute",
                    'retry_after': result['reset_at'] - int(time.time())
                },
                status=429  # Too Many Requests
            )

        return response
```

#### 4. Quota Tracking (Database)

```sql
-- Quota tracking table
CREATE TABLE organization_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,

    -- Subscription tier
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise', 'custom')),

    -- Scan quotas
    scans_limit_monthly INT NOT NULL DEFAULT 100,
    scans_used_monthly INT NOT NULL DEFAULT 0,

    -- Storage quotas (in bytes)
    storage_limit_bytes BIGINT NOT NULL DEFAULT 1073741824,  -- 1GB
    storage_used_bytes BIGINT NOT NULL DEFAULT 0,

    -- Concurrency limits
    concurrent_scans_limit INT NOT NULL DEFAULT 2,

    -- Reset tracking
    quota_period_start TIMESTAMPTZ NOT NULL DEFAULT DATE_TRUNC('month', NOW()),
    quota_period_end TIMESTAMPTZ NOT NULL DEFAULT (DATE_TRUNC('month', NOW()) + INTERVAL '1 month'),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_org_quotas_org ON organization_quotas(org_id);

-- Quota tiers
CREATE TABLE quota_tiers (
    tier TEXT PRIMARY KEY,
    scans_limit_monthly INT NOT NULL,
    storage_limit_gb INT NOT NULL,
    concurrent_scans_limit INT NOT NULL,
    api_rate_limit_per_min INT NOT NULL,
    price_per_month_cents INT NOT NULL
);

INSERT INTO quota_tiers (tier, scans_limit_monthly, storage_limit_gb, concurrent_scans_limit, api_rate_limit_per_min, price_per_month_cents) VALUES
    ('free', 100, 1, 2, 60, 0),
    ('pro', 1000, 10, 10, 600, 4900),
    ('enterprise', 10000, 100, 50, 6000, 29900);
```

#### 5. Quota Service

```python
# services/quota_service.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

class QuotaExceeded(Exception):
    pass

class QuotaService:
    """
    Manage organization quotas.
    """

    @staticmethod
    def check_scan_quota(org_id):
        """
        Check if organization can start a new scan.
        Raises QuotaExceeded if limit reached.
        """
        with transaction.atomic():
            quota = OrganizationQuota.objects.select_for_update().get(org_id=org_id)

            # Check if we need to reset monthly quota
            if timezone.now() >= quota.quota_period_end:
                quota.scans_used_monthly = 0
                quota.quota_period_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                quota.quota_period_end = quota.quota_period_start + timedelta(days=32)
                quota.quota_period_end = quota.quota_period_end.replace(day=1)
                quota.save()

            # Check monthly quota
            if quota.scans_used_monthly >= quota.scans_limit_monthly:
                raise QuotaExceeded(
                    f"Monthly scan quota exceeded ({quota.scans_limit_monthly} scans). "
                    f"Resets on {quota.quota_period_end.strftime('%Y-%m-%d')}"
                )

            # Check concurrent scans
            running_scans = Scan.objects.filter(
                project__org_id=org_id,
                status='running'
            ).count()

            if running_scans >= quota.concurrent_scans_limit:
                raise QuotaExceeded(
                    f"Concurrent scan limit exceeded ({quota.concurrent_scans_limit} scans). "
                    f"Please wait for running scans to complete."
                )

            # Increment usage
            quota.scans_used_monthly += 1
            quota.save(update_fields=['scans_used_monthly', 'updated_at'])

            return {
                'scans_remaining': quota.scans_limit_monthly - quota.scans_used_monthly,
                'concurrent_scans_remaining': quota.concurrent_scans_limit - running_scans - 1,
            }

    @staticmethod
    def check_storage_quota(org_id, additional_bytes):
        """
        Check if adding storage would exceed quota.
        """
        quota = OrganizationQuota.objects.get(org_id=org_id)

        if quota.storage_used_bytes + additional_bytes > quota.storage_limit_bytes:
            raise QuotaExceeded(
                f"Storage quota exceeded. "
                f"Limit: {quota.storage_limit_bytes / 1e9:.2f} GB, "
                f"Used: {quota.storage_used_bytes / 1e9:.2f} GB"
            )

    @staticmethod
    def increment_storage(org_id, bytes_added):
        """
        Increment storage usage after uploading SARIF.
        """
        OrganizationQuota.objects.filter(org_id=org_id).update(
            storage_used_bytes=models.F('storage_used_bytes') + bytes_added
        )

    @staticmethod
    def get_quota_usage(org_id):
        """
        Get current quota usage for organization.
        """
        quota = OrganizationQuota.objects.get(org_id=org_id)
        running_scans = Scan.objects.filter(
            project__org_id=org_id,
            status='running'
        ).count()

        return {
            'tier': quota.tier,
            'scans': {
                'used': quota.scans_used_monthly,
                'limit': quota.scans_limit_monthly,
                'remaining': quota.scans_limit_monthly - quota.scans_used_monthly,
                'resets_at': quota.quota_period_end.isoformat(),
            },
            'storage': {
                'used_bytes': quota.storage_used_bytes,
                'used_gb': quota.storage_used_bytes / 1e9,
                'limit_bytes': quota.storage_limit_bytes,
                'limit_gb': quota.storage_limit_bytes / 1e9,
                'remaining_gb': (quota.storage_limit_bytes - quota.storage_used_bytes) / 1e9,
            },
            'concurrent_scans': {
                'running': running_scans,
                'limit': quota.concurrent_scans_limit,
                'remaining': quota.concurrent_scans_limit - running_scans,
            },
        }
```

#### 6. Integration with Scan Workflow

```python
# workers/scan_worker.py
from services.quota_service import QuotaService, QuotaExceeded

@shared_task
def run_security_scan(scan_id):
    scan = Scan.objects.select_related('project').get(id=scan_id)
    org_id = scan.project.org_id

    try:
        # Check scan quota BEFORE starting scan
        quota_info = QuotaService.check_scan_quota(org_id)

        # Publish quota info to SSE stream
        publish_progress(scan_id, {
            'status': 'running',
            'progress': 0,
            'step': 'Starting scan',
            'quota_remaining': quota_info['scans_remaining'],
        })

        # Run scan...
        sarif_data = perform_scan(scan)

        # Check storage quota before uploading SARIF
        sarif_size = len(json.dumps(sarif_data).encode('utf-8'))
        QuotaService.check_storage_quota(org_id, sarif_size)

        # Upload SARIF
        sarif_url = upload_sarif(org_id, scan_id, sarif_data)

        # Increment storage usage
        QuotaService.increment_storage(org_id, sarif_size)

        # Complete scan...

    except QuotaExceeded as e:
        scan.status = 'failed'
        scan.error_message = str(e)
        scan.save()

        # Decrement scan count (scan didn't actually run)
        OrganizationQuota.objects.filter(org_id=org_id).update(
            scans_used_monthly=models.F('scans_used_monthly') - 1
        )

        raise
```

#### 7. API Endpoints for Quota Management

```python
# views/quotas.py
@api_view(['GET'])
@permission_classes([OrganizationPermission])
def get_quota_usage(request):
    """
    Get current quota usage for organization.
    """
    usage = QuotaService.get_quota_usage(request.org_id)
    return Response(usage)

@api_view(['POST'])
@permission_classes([OrganizationPermission, IsOrgOwner])
def upgrade_tier(request):
    """
    Upgrade organization to higher tier.
    """
    new_tier = request.data.get('tier')
    if new_tier not in ['pro', 'enterprise']:
        return Response({'error': 'Invalid tier'}, status=400)

    # Get tier limits
    tier_config = QuotaTier.objects.get(tier=new_tier)

    # Update quota
    quota = OrganizationQuota.objects.get(org_id=request.org_id)
    quota.tier = new_tier
    quota.scans_limit_monthly = tier_config.scans_limit_monthly
    quota.storage_limit_bytes = tier_config.storage_limit_gb * 1e9
    quota.concurrent_scans_limit = tier_config.concurrent_scans_limit
    quota.save()

    # Update organization
    org = Organization.objects.get(id=request.org_id)
    org.subscription_tier = new_tier
    org.save()

    return Response({
        'message': f'Upgraded to {new_tier} tier',
        'new_limits': QuotaService.get_quota_usage(request.org_id)
    })
```

#### 8. User-Facing Error Messages

```javascript
// Frontend handling of quota errors
async function triggerScan(projectId, branchId) {
    try {
        const response = await fetch('/api/scans', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, branch_id: branchId }),
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.status === 429) {
            const data = await response.json();
            if (data.error_code === 'QUOTA_EXCEEDED') {
                showUpgradeModal(data.message, data.current_tier, data.recommended_tier);
            } else if (data.error_code === 'RATE_LIMIT_EXCEEDED') {
                showRateLimitMessage(data.retry_after);
            }
        }

    } catch (error) {
        console.error('Scan failed:', error);
    }
}
```

#### 9. Monitoring & Alerts

```python
# monitoring/quota_alerts.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def check_quota_usage_alerts():
    """
    Check for orgs approaching quota limits and send alerts.
    Run daily via cron.
    """
    quotas = OrganizationQuota.objects.select_related('organization').all()

    for quota in quotas:
        usage_pct = (quota.scans_used_monthly / quota.scans_limit_monthly) * 100

        # Alert at 80% usage
        if usage_pct >= 80 and usage_pct < 100:
            send_quota_warning_email(
                org=quota.organization,
                usage_pct=usage_pct,
                resets_at=quota.quota_period_end
            )

        # Alert when quota exceeded
        elif usage_pct >= 100:
            send_quota_exceeded_email(
                org=quota.organization,
                resets_at=quota.quota_period_end
            )
```

## Consequences

### Positive

- **Abuse prevention:** Rate limits and quotas prevent infrastructure overload
- **Fair resource allocation:** All orgs get guaranteed minimum resources
- **Cost control:** Predictable infrastructure costs based on tier limits
- **Clear user feedback:** Informative error messages with upgrade prompts
- **Billing integration:** Quota usage can drive metered billing
- **Monitoring:** Visibility into resource consumption patterns

### Negative

- **User friction:** Users may hit limits unexpectedly
- **Support burden:** Need to handle quota increase requests
- **Complexity:** Two systems (Redis + PostgreSQL) to manage

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Redis failure breaks rate limiting | Graceful degradation (allow requests); monitor Redis health |
| Quota tracking out of sync | Periodic reconciliation job; atomic increments |
| Users frustrated by limits | Clear upgrade path; generous free tier; email warnings at 80% |
| Quota reset timing issues | Use database transactions; idempotent reset logic |

## Related Decisions

- **ADR-001:** Multi-tenancy (quotas enforced per org_id)
- **ADR-003:** Real-time communication (Redis already available for rate limiting)
- **ADR-004:** Worker security (concurrent scan limits prevent resource exhaustion)
- **ADR-007:** Authentication (org_id from JWT used for rate limiting)

## References

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Redis Rate Limiting Patterns](https://redis.io/docs/manual/patterns/rate-limiter/)
- [HTTP 429 Too Many Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
- [Stripe Rate Limiting](https://stripe.com/docs/rate-limits)
- [GitHub Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
