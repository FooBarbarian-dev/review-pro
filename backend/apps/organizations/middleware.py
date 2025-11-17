"""
Row-Level Security (RLS) middleware for automatic session context management.

This middleware automatically sets the PostgreSQL session variable used by
RLS policies to enforce multi-tenancy at the database level.
"""
import logging
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RowLevelSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to set PostgreSQL session context for Row-Level Security.

    Sets app.current_user_id session variable for each authenticated request,
    enabling RLS policies to enforce organization-level isolation at the
    database layer (ADR-001).

    This provides defense-in-depth: even if application-level filtering
    fails, RLS prevents data leakage.
    """

    def process_request(self, request):
        """
        Set RLS context at the start of each request.

        Args:
            request: Django request object

        Returns:
            None (continues request processing)
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                self.set_rls_context(request.user.id)
                logger.debug(f"RLS context set for user {request.user.id}")
            except Exception as e:
                logger.error(f"Failed to set RLS context: {e}")
                # Don't fail the request, RLS is defense-in-depth
        else:
            # Anonymous request - clear any existing context
            try:
                self.clear_rls_context()
            except Exception as e:
                logger.debug(f"Failed to clear RLS context: {e}")

        return None

    def process_response(self, request, response):
        """
        Clear RLS context at the end of each request.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            response (unchanged)
        """
        try:
            self.clear_rls_context()
            logger.debug("RLS context cleared")
        except Exception as e:
            logger.debug(f"Failed to clear RLS context: {e}")

        return response

    def process_exception(self, request, exception):
        """
        Clear RLS context on exception.

        Args:
            request: Django request object
            exception: Exception that occurred

        Returns:
            None (allows exception to propagate)
        """
        try:
            self.clear_rls_context()
        except Exception as e:
            logger.debug(f"Failed to clear RLS context on exception: {e}")

        return None

    @staticmethod
    def set_rls_context(user_id):
        """
        Set PostgreSQL session variable for RLS policies.

        Args:
            user_id: UUID of the authenticated user
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SET SESSION app.current_user_id = %s",
                [str(user_id)]
            )

    @staticmethod
    def clear_rls_context():
        """Clear PostgreSQL session variable for RLS policies."""
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_user_id")


class RLSContextManager:
    """
    Context manager for temporarily setting RLS context.

    Useful for background tasks, Celery workers, or testing.

    Usage:
        with RLSContextManager(user_id):
            # All queries filtered by RLS for this user
            orgs = Organization.objects.all()
    """

    def __init__(self, user_id):
        """
        Initialize context manager.

        Args:
            user_id: UUID of user to set context for
        """
        self.user_id = user_id

    def __enter__(self):
        """Set RLS context on enter."""
        RowLevelSecurityMiddleware.set_rls_context(self.user_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear RLS context on exit."""
        RowLevelSecurityMiddleware.clear_rls_context()
        return False  # Don't suppress exceptions


# Convenience functions for manual RLS management
def set_rls_user(user_id):
    """
    Set RLS context for a user.

    Args:
        user_id: UUID of user
    """
    RowLevelSecurityMiddleware.set_rls_context(user_id)


def clear_rls_user():
    """Clear RLS context."""
    RowLevelSecurityMiddleware.clear_rls_context()


def with_rls_context(user_id):
    """
    Decorator to run a function with RLS context.

    Args:
        user_id: UUID of user to set context for

    Usage:
        @with_rls_context(user.id)
        def my_function():
            # All queries filtered by RLS
            return Organization.objects.all()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with RLSContextManager(user_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator
