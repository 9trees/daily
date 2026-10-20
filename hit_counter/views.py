import json
import re
from functools import wraps

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Hit, Page
from .services import client_ip, counts_for, location_for


def error(message: str, status: int) -> JsonResponse:
    return JsonResponse({'error': message}, status=status)


def public_endpoint(method):
    def decorate(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            origin = request.headers.get('Origin')
            if origin and origin not in settings.HIT_COUNTER_ALLOWED_ORIGINS:
                response = error('Origin is not allowed.', 403)
            elif request.method == 'OPTIONS':
                requested_method = request.headers.get('Access-Control-Request-Method')
                requested_headers = {
                    header.strip().lower()
                    for header in request.headers.get(
                        'Access-Control-Request-Headers', ''
                    ).split(',') if header.strip()
                }
                if requested_method and requested_method != method:
                    response = error('Requested method is not allowed.', 405)
                elif requested_headers - {'content-type'}:
                    response = error('Requested headers are not allowed.', 400)
                else:
                    response = HttpResponse(status=204)
            elif request.method != method:
                response = error('Method is not allowed.', 405)
            else:
                response = view(request, *args, **kwargs)
            response['Allow'] = '{}, OPTIONS'.format(method)
            response['Cache-Control'] = 'no-store'
            response['Vary'] = 'Origin'
            if origin in settings.HIT_COUNTER_ALLOWED_ORIGINS:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Methods'] = '{}, OPTIONS'.format(method)
                response['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        return wrapped
    return decorate


@public_endpoint('POST')
def log_hit(request: HttpRequest) -> JsonResponse:
    if request.content_type != 'application/json':
        return error('Content-Type must be application/json.', 415)
    body = request.read(1025)
    if len(body) > 1024:
        return error('Request body must not exceed 1024 bytes.', 413)
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return error('Request body must be valid JSON.', 400)
    if not isinstance(payload, dict):
        return error('Request body must be a JSON object.', 400)
    code = payload.get('page')
    if not isinstance(code, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', code):
        return error('page must be a page code of 1-100 letters, digits, _ or -.', 400)
    if set(payload) != {'page'}:
        return error('Only the page field is accepted.', 400)
    page = Page.objects.filter(code=code, is_active=True).first()
    if page is None:
        return error('Page not found or inactive.', 404)
    try:
        address = client_ip(request)
    except ValueError:
        return error('A valid client IP address is required.', 400)
    hit = Hit.objects.create(page=page, ip_address=address, **location_for(address))
    return JsonResponse({
        **counts_for(page),
        'logged_at': hit.created_at.isoformat(),
        'location_status': hit.location_status,
    }, status=201)


@public_endpoint('GET')
def hit_count(request: HttpRequest, code: str) -> JsonResponse:
    page = Page.objects.filter(code=code, is_active=True).first()
    if page is None:
        return error('Page not found or inactive.', 404)
    return JsonResponse(counts_for(page))
