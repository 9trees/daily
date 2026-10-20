import ipaddress
import sys
from typing import List
from urllib.parse import urlsplit

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
else:
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def split_lines(value: str) -> List[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def validate_origins(value: str) -> None:
    for origin in split_lines(value):
        parts = urlsplit(origin)
        if (
            parts.scheme not in {'http', 'https'} or not parts.hostname
            or parts.path or parts.query or parts.fragment or parts.username
            or '{}://{}'.format(parts.scheme, parts.netloc) != origin
        ):
            raise ValidationError(
                '"%(origin)s" is not an origin such as https://9trees.github.io '
                '(no path or trailing slash).', params={'origin': origin},
            )


def validate_ips(value: str) -> None:
    for address in split_lines(value):
        try:
            ipaddress.ip_address(address)
        except ValueError:
            raise ValidationError(
                '"%(ip)s" is not a valid IP address.', params={'ip': address},
            )


def validate_time_zone(value: str) -> None:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationError(
            '"%(zone)s" is not a valid IANA timezone, e.g. UTC or Asia/Kolkata.',
            params={'zone': value},
        )


class CounterSettings(models.Model):
    """Single admin-editable configuration row for the counter."""

    allowed_origins = models.TextField(
        default='https://9trees.github.io', blank=True, validators=[validate_origins],
        help_text='One browser origin per line, e.g. https://9trees.github.io '
                  '(no path or trailing slash). Requests without an Origin header '
                  'are always accepted.',
    )
    time_zone = models.CharField(
        max_length=64, default='UTC', validators=[validate_time_zone],
        help_text='IANA timezone used for "today" counts, e.g. UTC or Asia/Kolkata.',
    )
    geoip_path = models.CharField(
        'GeoIP database path', max_length=500, blank=True,
        help_text='Absolute path to a local GeoLite2 City .mmdb file on the server. '
                  'Leave empty to skip location lookup.',
    )
    trusted_proxy_ips = models.TextField(
        'trusted proxy IPs', blank=True, validators=[validate_ips],
        help_text='One IP per line. Only requests whose REMOTE_ADDR is listed here '
                  'use the last X-Forwarded-For entry as the visitor IP.',
    )

    class Meta:
        verbose_name = 'counter settings'
        verbose_name_plural = 'counter settings'

    def __str__(self):
        return 'Counter settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'CounterSettings':
        return cls.objects.filter(pk=1).first() or cls()

    @property
    def origin_list(self) -> List[str]:
        return split_lines(self.allowed_origins)

    @property
    def proxy_ip_list(self) -> List[str]:
        return [str(ipaddress.ip_address(ip)) for ip in split_lines(self.trusted_proxy_ips)]


class Page(models.Model):
    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class Hit(models.Model):
    class LocationStatus(models.TextChoices):
        FOUND = 'found', 'Found'
        NOT_CONFIGURED = 'not_configured', 'Database not configured'
        NOT_FOUND = 'not_found', 'IP not in database'
        LOOKUP_FAILED = 'lookup_failed', 'Lookup failed'

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='hits')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    location_status = models.CharField(max_length=20, choices=LocationStatus.choices)

    class Meta:
        indexes = [
            models.Index(fields=['page', 'created_at'], name='hit_page_created_idx'),
        ]
