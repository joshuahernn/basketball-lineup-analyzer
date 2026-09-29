"""Serve the built Angular entry point for the combined deployment."""

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe


@require_safe
def dashboard(request):
    try:
        index = (settings.FRONTEND_DIST_DIR / 'index.html').open('rb')
    except FileNotFoundError as error:
        raise Http404('The frontend has not been built.') from error

    response = FileResponse(index, content_type='text/html')
    response['Cache-Control'] = 'no-cache'
    return response
