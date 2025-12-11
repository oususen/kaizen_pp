from django.conf import settings
from django.middleware.csrf import get_token


class EnsureCSRFCookieMiddleware:
    """Always issue a CSRF cookie so SPA clients can pick it up."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.CSRF_COOKIE_NAME not in request.COOKIES:
            get_token(request)
        return self.get_response(request)
