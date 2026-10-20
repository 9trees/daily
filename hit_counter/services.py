import ipaddress
import logging
import sys
from datetime import datetime, time, timedelta
from typing import Dict

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    from backports.zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpRequest
from django.utils import timezone
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError
from maxminddb.errors import InvalidDatabaseError

from .models import Hit, Page


logger = logging.getLogger(__name__)


def client_ip(request: HttpRequest) -> str:
    address = str(ipaddress.ip_address(request.META.get('REMOTE_ADDR', '')))
    if address in settings.HIT_COUNTER_TRUSTED_PROXY_IPS:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            # The trusted immediate proxy must append the actual peer address.
            address = str(ipaddress.ip_address(forwarded.split(',')[-1].strip()))
    return address


def location_for(address: str) -> Dict[str, str]:
    path = settings.HIT_COUNTER_GEOIP_PATH
    if not path:
        return {'location_status': Hit.LocationStatus.NOT_CONFIGURED}
    try:
        with Reader(path) as reader:
            result = reader.city(address)
            return {
                'country': result.country.name or '',
                'region': result.subdivisions.most_specific.name or '',
                'city': result.city.name or '',
                'location_status': Hit.LocationStatus.FOUND,
            }
    except AddressNotFoundError:
        return {'location_status': Hit.LocationStatus.NOT_FOUND}
    except (OSError, InvalidDatabaseError, ValueError):
        logger.exception('Local hit-counter GeoIP lookup failed')
        return {'location_status': Hit.LocationStatus.LOOKUP_FAILED}


def counts_for(page: Page) -> dict:
    zone = ZoneInfo(settings.HIT_COUNTER_TIME_ZONE)
    today = timezone.now().astimezone(zone).date()
    start = datetime.combine(today, time.min, tzinfo=zone)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone)
    counts = page.hits.aggregate(
        total_hits=Count('pk'),
        today_hits=Count('pk', filter=Q(created_at__gte=start, created_at__lt=end)),
    )
    return {
        'page': page.code,
        **counts,
        'date': today.isoformat(),
        'timezone': settings.HIT_COUNTER_TIME_ZONE,
    }
