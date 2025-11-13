# ADR-007: Authentication & Authorization

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team, Security Team
**Technical Story:** User authentication and role-based access control

## Context and Problem Statement

Our security analysis platform needs:
1. **Authentication:** Verify user identity (who are you?)
2. **Authorization:** Verify user permissions (what can you do?)
3. **GitHub integration:** Allow users to connect their GitHub accounts and authorize repository access
4. **Multi-organization support:** Users can belong to multiple organizations with different roles

Key decisions:
- Session-based auth vs JWT tokens?
- OAuth integration (GitHub, GitLab, etc.)?
- Role-based access control (RBAC) model?
- API authentication for programmatic access?

## Decision Drivers

- **Security:** Industry-standard authentication mechanisms
- **User experience:** SSO via GitHub for frictionless onboarding
- **Scalability:** Stateless authentication for horizontal scaling
- **Developer experience:** Simple API authentication for CI/CD integration
- **Compliance:** Audit trail for all access (SOC 2 requirement)

## Considered Options

### Option 1: Session-Based Authentication

Traditional cookie-based sessions stored in Redis/PostgreSQL.

**Pros:**
- Simple to implement (Django built-in)
- Easy to revoke sessions (delete from store)
- Familiar to developers

**Cons:**
- Stateful (requires session store)
- Harder to scale horizontally (session stickiness)
- Not suitable for API clients
- CSRF protection complexity

### Option 2: JWT (JSON Web Tokens)

Stateless tokens signed with secret key, containing user claims.

**Pros:**
- Stateless (no server-side storage)
- Scales horizontally (no session stickiness)
- Self-contained (includes user info)
- Works for both web and API

**Cons:**
- Can't revoke tokens before expiration (mitigated by short TTL + refresh tokens)
- Token size (can be large with many claims)
- Clock skew issues (mitigated by `iat` and `exp` claims)

### Option 3: Hybrid (Session for Web, JWT for API)

Use session cookies for web app, JWT for programmatic API access.

**Pros:**
- Best of both worlds
- Easy revocation for web sessions
- Stateless tokens for API clients

**Cons:**
- Two authentication systems to maintain
- More complex implementation

## Decision Outcome

**Chosen option:** Option 2 - JWT with refresh tokens for both web and API.

### Justification

1. **Stateless architecture:** No session storage required, easier horizontal scaling
2. **Unified authentication:** Same mechanism for web and API
3. **Mobile-friendly:** JWTs work naturally with mobile apps
4. **Short-lived access tokens + refresh tokens:** Mitigates revocation concerns
5. **Industry standard:** Well-understood, many libraries available

**Revocation strategy:** Short-lived access tokens (15 minutes) + long-lived refresh tokens (30 days) stored in database for revocation.

### Implementation Strategy

#### 1. Token Structure

**Access Token (JWT):**
- **Purpose:** Authenticate API requests
- **TTL:** 15 minutes
- **Storage:** Client-side only (localStorage or memory)
- **Claims:**
  ```json
  {
    "sub": "user_id",
    "email": "user@example.com",
    "org_id": "current_org_id",
    "role": "admin",
    "iat": 1699900800,
    "exp": 1699901700
  }
  ```

**Refresh Token:**
- **Purpose:** Obtain new access token
- **TTL:** 30 days
- **Storage:** Database (for revocation) + HTTP-only cookie
- **Structure:** Opaque token (UUID), not JWT

#### 2. Database Schema

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hash of token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id, revoked_at);
CREATE INDEX idx_refresh_tokens_expiry ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;

-- Cleanup job: Delete expired tokens daily
CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
```

#### 3. Authentication Endpoints

```python
# views/auth.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import jwt
import secrets
import hashlib

# JWT Configuration
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)

def create_access_token(user, org_membership):
    """Create short-lived JWT access token."""
    now = timezone.now()
    payload = {
        'sub': str(user.id),
        'email': user.email,
        'name': user.name,
        'org_id': str(org_membership.organization_id),
        'role': org_membership.role,
        'iat': int(now.timestamp()),
        'exp': int((now + ACCESS_TOKEN_TTL).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user):
    """Create long-lived refresh token and store in database."""
    # Generate cryptographically secure random token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Store in database
    refresh_token = RefreshToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=timezone.now() + REFRESH_TOKEN_TTL
    )

    return token

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with email and password.
    Returns access token (short-lived) and refresh token (long-lived).
    """
    email = request.data.get('email')
    password = request.data.get('password')
    org_slug = request.data.get('organization')  # Optional: switch org on login

    # Authenticate user
    user = User.objects.filter(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Get organization membership
    if org_slug:
        org_membership = OrganizationMember.objects.filter(
            user=user,
            organization__slug=org_slug
        ).select_related('organization').first()
    else:
        # Default to first org
        org_membership = OrganizationMember.objects.filter(
            user=user
        ).select_related('organization').first()

    if not org_membership:
        return Response(
            {'error': 'No organization access'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Create tokens
    access_token = create_access_token(user, org_membership)
    refresh_token = create_refresh_token(user)

    # Set refresh token as HTTP-only cookie
    response = Response({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': int(ACCESS_TOKEN_TTL.total_seconds()),
        'user': {
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
        },
        'organization': {
            'id': str(org_membership.organization_id),
            'name': org_membership.organization.name,
            'slug': org_membership.organization.slug,
            'role': org_membership.role,
        }
    })

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        httponly=True,
        secure=True,  # HTTPS only
        samesite='Lax'
    )

    return response

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh(request):
    """
    Refresh access token using refresh token.
    """
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        return Response(
            {'error': 'No refresh token provided'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Hash token for lookup
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    # Find token in database
    token_record = RefreshToken.objects.filter(
        token_hash=token_hash,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now()
    ).select_related('user').first()

    if not token_record:
        return Response(
            {'error': 'Invalid or expired refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Update last_used_at
    token_record.last_used_at = timezone.now()
    token_record.save(update_fields=['last_used_at'])

    # Get current org membership (from query param or default)
    org_slug = request.GET.get('organization')
    if org_slug:
        org_membership = OrganizationMember.objects.filter(
            user=token_record.user,
            organization__slug=org_slug
        ).select_related('organization').first()
    else:
        org_membership = OrganizationMember.objects.filter(
            user=token_record.user
        ).select_related('organization').first()

    # Create new access token
    access_token = create_access_token(token_record.user, org_membership)

    return Response({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': int(ACCESS_TOKEN_TTL.total_seconds()),
    })

@api_view(['POST'])
def logout(request):
    """
    Logout: Revoke refresh token.
    """
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        RefreshToken.objects.filter(token_hash=token_hash).update(
            revoked_at=timezone.now()
        )

    response = Response({'message': 'Logged out successfully'})
    response.delete_cookie('refresh_token')
    return response
```

#### 4. JWT Authentication Middleware

```python
# middleware/jwt_auth.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
import jwt

class JWTAuthentication(BaseAuthentication):
    """
    JWT authentication for API requests.
    Expects: Authorization: Bearer <token>
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            # Parse "Bearer <token>"
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return None

            # Decode JWT
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )

            # Get user from database
            user_id = payload.get('sub')
            user = User.objects.get(id=user_id, is_active=True)

            # Attach org context to request
            request.org_id = payload.get('org_id')
            request.user_role = payload.get('role')

            return (user, token)

        except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            raise AuthenticationFailed('Invalid or expired token')

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'middleware.jwt_auth.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### 5. GitHub OAuth Integration

```python
# views/oauth.py
import requests
from django.shortcuts import redirect
from django.conf import settings

@api_view(['GET'])
@permission_classes([AllowAny])
def github_login(request):
    """
    Redirect to GitHub OAuth authorization page.
    """
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=read:user,user:email,repo"
    )
    return redirect(github_auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
def github_callback(request):
    """
    Handle GitHub OAuth callback.
    Exchange code for access token, fetch user info, create/login user.
    """
    code = request.GET.get('code')
    if not code:
        return Response({'error': 'No code provided'}, status=400)

    # Exchange code for access token
    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        headers={'Accept': 'application/json'},
        data={
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': code,
        }
    )
    github_token = token_response.json().get('access_token')

    # Fetch user info from GitHub
    user_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'Bearer {github_token}'}
    )
    github_user = user_response.json()

    # Find or create user
    user, created = User.objects.get_or_create(
        email=github_user['email'],
        defaults={
            'name': github_user['name'] or github_user['login'],
            'github_id': github_user['id'],
        }
    )

    # Create org membership if new user (default personal org)
    if created:
        org = Organization.objects.create(
            name=f"{user.name}'s Organization",
            slug=generate_slug(user.name)
        )
        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role='owner'
        )

    # Create tokens and return
    org_membership = OrganizationMember.objects.filter(user=user).first()
    access_token = create_access_token(user, org_membership)
    refresh_token = create_refresh_token(user)

    # Redirect to frontend with token
    frontend_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
    return redirect(frontend_url)
```

#### 6. Authorization (RBAC)

```python
# permissions.py
from rest_framework.permissions import BasePermission

class OrganizationPermission(BasePermission):
    """
    Role-based permissions within organization.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check organization membership
        org_id = request.org_id
        if not org_id:
            return False

        # Set PostgreSQL context for RLS
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org_id', %s, true)",
                [str(org_id)]
            )

        return True

    def has_object_permission(self, request, view, obj):
        # Verify object belongs to user's org
        if hasattr(obj, 'org_id'):
            return str(obj.org_id) == str(request.org_id)
        return False

class IsOrgAdmin(BasePermission):
    """
    Only org admins and owners can perform action.
    """

    def has_permission(self, request, view):
        return request.user_role in ['admin', 'owner']

class IsOrgOwner(BasePermission):
    """
    Only org owners can perform action.
    """

    def has_permission(self, request, view):
        return request.user_role == 'owner'

# Usage in views
@api_view(['POST'])
@permission_classes([OrganizationPermission, IsOrgAdmin])
def create_project(request):
    """Only admins/owners can create projects."""
    # ...

@api_view(['DELETE'])
@permission_classes([OrganizationPermission, IsOrgOwner])
def delete_organization(request, org_id):
    """Only owners can delete organization."""
    # ...
```

#### 7. API Keys for Programmatic Access

```python
# For CI/CD integrations
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,  -- "CI/CD Pipeline", "GitHub Actions", etc.
    key_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hash of API key
    key_prefix TEXT NOT NULL,  -- First 8 chars for identification (sk_live_12345678...)
    scopes TEXT[] DEFAULT ARRAY['read:scans', 'write:scans'],  -- Permissions
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

# API key format: sca_<env>_<random_32_chars>
# Example: sca_prod_9k3j2h1g9f8d7c6b5a4z3x2w1v0u9t8s

@api_view(['POST'])
@permission_classes([OrganizationPermission, IsOrgAdmin])
def create_api_key(request):
    """
    Create API key for programmatic access.
    Returns full key ONCE (never stored, only hash).
    """
    name = request.data.get('name')
    scopes = request.data.get('scopes', ['read:scans', 'write:scans'])

    # Generate API key (sca = security code analysis)
    random_part = secrets.token_urlsafe(32)
    env = settings.ENVIRONMENT  # 'prod' or 'dev'
    api_key = f"sca_{env}_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:16]  # "sca_prod_1234567"

    # Store hash in database
    api_key_record = ApiKey.objects.create(
        org_id=request.org_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        created_by=request.user
    )

    return Response({
        'id': str(api_key_record.id),
        'api_key': api_key,  # Return ONCE, never again
        'key_prefix': key_prefix,
        'scopes': scopes,
        'warning': 'Save this key securely. You will not be able to see it again.'
    })
```

## Consequences

### Positive

- **Stateless authentication:** Easy horizontal scaling
- **Unified mechanism:** Same auth for web and API
- **Short-lived tokens:** Reduced security risk
- **GitHub SSO:** Frictionless onboarding
- **API keys:** CI/CD integration without user credentials
- **RBAC:** Fine-grained permissions per organization

### Negative

- **Token revocation complexity:** Must track refresh tokens in database
- **Clock skew issues:** Require NTP synchronization
- **Token size:** JWTs can be large (mitigated by minimal claims)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Stolen access token | Short TTL (15 min); monitor for unusual activity |
| Stolen refresh token | Store hash in DB; revoke on logout; detect concurrent use |
| JWT secret compromise | Rotate secret; invalidate all tokens; force re-login |
| API key leak | Prefix for identification; revoke key; audit logs |
| Clock skew | Use NTP; allow small clock drift (30s); include `iat` claim |

## Related Decisions

- **ADR-001:** Multi-tenancy (org_id in JWT claims, RLS context)
- **ADR-004:** Worker security (GitHub App tokens for repo access)
- **ADR-006:** Data model (organization_members for RBAC)

## References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [GitHub OAuth Documentation](https://docs.github.com/en/apps/oauth-apps)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Django REST Framework JWT](https://www.django-rest-framework.org/api-guide/authentication/)
