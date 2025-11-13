"""
Custom exception handler for DRF.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that logs errors and returns consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response data
        custom_response_data = {
            'error': {
                'message': str(exc),
                'type': exc.__class__.__name__,
                'status_code': response.status_code,
            }
        }

        # Add detail if available
        if hasattr(exc, 'detail'):
            custom_response_data['error']['detail'] = exc.detail

        response.data = custom_response_data

        # Log the error
        logger.error(
            f"API Error: {exc.__class__.__name__} - {str(exc)}",
            extra={
                'status_code': response.status_code,
                'path': context.get('request').path if context.get('request') else None,
                'method': context.get('request').method if context.get('request') else None,
            }
        )
    else:
        # Handle non-DRF exceptions
        logger.exception(f"Unhandled exception: {str(exc)}")
        response = Response(
            {
                'error': {
                    'message': 'An unexpected error occurred.',
                    'type': 'InternalServerError',
                    'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
