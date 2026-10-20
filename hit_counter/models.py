from django.db import models
from django.utils import timezone


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
