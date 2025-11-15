# Rate Limiting Configuration Guide

**Status:** Configured - Needs Application
**Priority:** Priority 3 (Advanced Feature)
**ADR:** ADR-008 Rate Limiting & Quotas

---

## Overview

Rate limiting protects the API from abuse by limiting the number of requests a user/IP can make within a time window. This complements quota management (which limits monthly scans) by preventing rapid-fire API abuse.

### Current Configuration

**Library:** `django-ratelimit`
**Backend:** Redis
**Status:** ✅ Configured in settings.py

```python
# backend/config/settings.py
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'  # Uses Redis
```

---

## Rate Limit Strategy (ADR-008)

### Per-Resource Limits

| Endpoint | Limit | Window | Reason |
|----------|-------|--------|--------|
| **Authentication** | | | |
| `POST /api/v1/auth/login/` | 5 req/min | Per IP | Prevent brute force |
| `POST /api/v1/auth/refresh/` | 10 req/min | Per user | Normal refresh rate |
| **Organizations** | | | |
| `GET /api/v1/organizations/` | 100 req/min | Per user | Normal browsing |
| `POST /api/v1/organizations/` | 10 req/hr | Per user | Prevent spam orgs |
| **Scans** | | | |
| `GET /api/v1/scans/` | 100 req/min | Per user | Normal monitoring |
| `POST /api/v1/scans/` | 30 req/hr | Per org | Prevent scan spam |
| **Findings** | | | |
| `GET /api/v1/findings/` | 200 req/min | Per user | Dashboards may poll |
| `POST /api/v1/findings/{id}/comments/` | 30 req/min | Per user | Prevent comment spam |

---

## Implementation

### Method 1: Decorator (Recommended)

Apply rate limits to specific views:

```python
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

class ScanViewSet(viewsets.ModelViewSet):
    @method_decorator(ratelimit(
        key='user',  # Rate limit per user
        rate='30/h',  # 30 requests per hour
        method='POST',  # Only POST requests
        block=True  # Block when limit exceeded
    ))
    def create(self, request, *args, **kwargs):
        """Create scan with rate limiting."""
        return super().create(request, *args, **kwargs)
```

### Method 2: Global Middleware

Apply rate limits globally (use cautiously):

```python
# backend/config/settings.py
MIDDLEWARE = [
    # ... other middleware ...
    'django_ratelimit.middleware.RatelimitMiddleware',
]

# Configure in views
@ratelimit(key='ip', rate='100/m', method='ALL')
def my_view(request):
    pass
```

### Method 3: Mixin

Create reusable rate limit mixin:

```python
# backend/apps/common/mixins.py
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

class RateLimitMixin:
    """Mixin to add rate limiting to viewsets."""

    rate_limit_key = 'user'  # Override in subclass
    rate_limit_rate = '100/m'  # Override in subclass
    rate_limit_methods = ['POST', 'PUT', 'PATCH', 'DELETE']

    @method_decorator(ratelimit(
        key=lambda r: r.user.id if r.user.is_authenticated else r.META.get('REMOTE_ADDR'),
        rate='100/m',
        block=True
    ))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# Usage
class ScanViewSet(RateLimitMixin, viewsets.ModelViewSet):
    rate_limit_rate = '30/h'  # Override default
```

---

## Rate Limit Keys

### Available Keys

```python
# Per authenticated user
ratelimit(key='user', rate='100/m')

# Per IP address
ratelimit(key='ip', rate='1000/h')

# Per user OR IP (for mixed auth/anon)
ratelimit(
    key=lambda r: r.user.id if r.user.is_authenticated else r.META.get('REMOTE_ADDR'),
    rate='100/m'
)

# Per organization (custom)
def org_key(request):
    if hasattr(request, 'organization'):
        return f"org:{request.organization.id}"
    return 'anon'

ratelimit(key=org_key, rate='1000/h')

# Per header (e.g., API key)
ratelimit(key='header:X-API-Key', rate='500/m')
```

---

## Rate Limit Formats

```python
# Requests per second
rate='10/s'

# Requests per minute
rate='100/m'

# Requests per hour
rate='1000/h'

# Requests per day
rate='10000/d'

# Multiple rates (most restrictive applies)
rate=['10/s', '100/m', '1000/h']
```

---

## Recommended Implementation

### Step 1: Apply to Authentication Endpoints

Update `backend/apps/authentication/views.py`:

```python
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

class CustomTokenObtainPairView(TokenObtainPairView):
    """Login with rate limiting."""

    @method_decorator(ratelimit(
        key='ip',
        rate='5/m',  # 5 login attempts per minute per IP
        method='POST',
        block=True
    ))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """Token refresh with rate limiting."""

    @method_decorator(ratelimit(
        key='user',
        rate='10/m',  # 10 refreshes per minute per user
        method='POST',
        block=True
    ))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
```

### Step 2: Apply to Scan Creation

Update `backend/apps/scans/views.py`:

```python
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

class ScanViewSet(viewsets.ModelViewSet):
    """Scan viewset with rate limiting."""

    def get_ratelimit_key(self, request):
        """Rate limit per organization."""
        try:
            repo = request.data.get('repository')
            if repo:
                repository = Repository.objects.get(id=repo)
                return f"org:{repository.organization_id}"
        except:
            pass
        return request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')

    @method_decorator(ratelimit(
        key='user',
        rate='30/h',  # 30 scans per hour per user
        method='POST',
        block=True
    ))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
```

### Step 3: Apply to Comment/Update Endpoints

Update `backend/apps/findings/views.py`:

```python
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

class FindingViewSet(viewsets.ModelViewSet):
    """Finding viewset with rate limiting."""

    @method_decorator(ratelimit(
        key='user',
        rate='30/m',  # 30 comments per minute
        method='POST',
        block=True
    ))
    @action(detail=True, methods=['post'])
    def comments(self, request, pk=None):
        """Add comment with rate limiting."""
        # ... implementation
```

---

## Custom Error Responses

By default, rate limit returns HTTP 429. Customize the response:

```python
from django_ratelimit.exceptions import Ratelimited
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """Handle rate limit exceptions with custom response."""
    if isinstance(exc, Ratelimited):
        return Response(
            {
                'error': 'Rate limit exceeded',
                'detail': 'Too many requests. Please try again later.',
                'retry_after': getattr(exc, 'retry_after', 60)  # seconds
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    return drf_exception_handler(exc, context)

# In settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}
```

---

## Testing Rate Limits

### Manual Testing

Test via API requests:

```bash
# 1. Test login rate limit (5/min)
for i in {1..10}; do
  echo "Attempt $i:"
  curl -X POST http://localhost:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}' \
    -w "\nStatus: %{http_code}\n"
  sleep 1
done

# Expected: First 5 succeed (or return 401), then 429 Too Many Requests

# 2. Test scan creation rate limit (30/hr)
TOKEN="your-jwt-token"

for i in {1..35}; do
  echo "Scan $i:"
  curl -X POST http://localhost:8000/api/v1/scans/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"repository": "repo-uuid", "branch": "branch-uuid"}' \
    -w "\nStatus: %{http_code}\n"
done

# Expected: First 30 succeed, then 429 Too Many Requests
```

### Automated Testing

Test in pytest:

```python
import pytest
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestRateLimiting:
    def test_login_rate_limit(self, client):
        """Test login endpoint has rate limit."""
        # Make 6 requests (limit is 5)
        for i in range(6):
            response = client.post('/api/v1/auth/login/', {
                'email': 'test@example.com',
                'password': 'wrongpass'
            })

            if i < 5:
                assert response.status_code in [200, 401]  # Normal response
            else:
                assert response.status_code == 429  # Rate limited

    def test_scan_creation_rate_limit(self, authenticated_client, repository, branch):
        """Test scan creation has rate limit."""
        # Make 31 scan requests (limit is 30/hr)
        for i in range(31):
            response = authenticated_client.post('/api/v1/scans/', {
                'repository': str(repository.id),
                'branch': str(branch.id)
            })

            if i < 30:
                assert response.status_code in [201, 400]  # Normal
            else:
                assert response.status_code == 429  # Rate limited
```

---

## Monitoring Rate Limits

### Check Redis Keys

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# List rate limit keys
KEYS rl:*

# Check specific key value
GET rl:ip:127.0.0.1:login:60

# Check TTL (time to live)
TTL rl:ip:127.0.0.1:login:60
```

### Django Admin Integration

Create admin view to see rate limit status:

```python
# backend/apps/common/admin.py
from django.contrib import admin
from django.core.cache import cache
import redis

@admin.register(RateLimitStatus)
class RateLimitStatusAdmin(admin.ModelAdmin):
    """View current rate limit status."""

    def get_queryset(self, request):
        # Return rate limit keys from Redis
        redis_client = redis.from_url(settings.REDIS_URL)
        keys = redis_client.keys('rl:*')

        # Parse and display
        # ... implementation
```

---

## Configuration Options

### Environment Variables

Add to `.env`:

```bash
# Enable/disable rate limiting
RATELIMIT_ENABLE=True

# Rate limit view (for testing)
RATELIMIT_VIEW=myapp.views.rate_limited

# Bypass for staff users
RATELIMIT_EXEMPT_STAFF=True
```

### Settings

```python
# backend/config/settings.py

# Enable rate limiting
RATELIMIT_ENABLE = env.bool('RATELIMIT_ENABLE', default=True)

# Use Redis for rate limit storage
RATELIMIT_USE_CACHE = 'default'

# Custom rate limit view
RATELIMIT_VIEW = 'myapp.views.rate_limited'

# Exempt staff users from rate limits (useful for testing)
# RATELIMIT_EXEMPT_STAFF = True  # DANGEROUS - only for dev
```

---

## Best Practices

1. **✅ Rate limit authentication endpoints** - Prevent brute force
2. **✅ Rate limit write operations** - Prevent spam/abuse
3. **✅ Use reasonable limits** - Don't block legitimate users
4. **✅ Monitor rate limit hits** - Identify abuse patterns
5. **✅ Provide clear error messages** - Include retry-after header
6. **⚠️ Don't rate limit read operations too aggressively** - Dashboards may poll
7. **⚠️ Consider per-organization limits** - Fair distribution
8. **⚠️ Test rate limits thoroughly** - Don't lock out users

---

## Troubleshooting

### Issue: "Rate limits not working"

**Check:**
1. Redis is running: `docker-compose ps redis`
2. Rate limiting enabled: `RATELIMIT_ENABLE=True`
3. Cache configured: `CACHES['default']` uses Redis
4. Decorator applied correctly

### Issue: "False positives (legitimate users blocked)"

**Solutions:**
- Increase rate limits
- Use per-user instead of per-IP
- Exempt authenticated users from IP limits
- Add bypass for API keys

### Issue: "Rate limits too strict for testing"

**Solution:** Disable in test environment:

```python
# backend/config/settings.py
if ENVIRONMENT == 'test':
    RATELIMIT_ENABLE = False
```

---

## Summary

**Configuration:**
- ✅ django-ratelimit installed
- ✅ Redis backend configured
- ⚠️ Need to apply decorators to views

**Recommended Limits:**
- Authentication: 5/min per IP
- Scan creation: 30/hr per user
- Comments: 30/min per user
- Read endpoints: 100-200/min per user

**Next Steps:**
1. Apply decorators to authentication views
2. Apply decorators to scan/finding views
3. Test rate limits
4. Monitor Redis for abuse patterns
5. Adjust limits based on usage

**Status:** Infrastructure ready, needs view decoration
