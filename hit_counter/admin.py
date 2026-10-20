from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import CounterSettings, Hit, Page


@admin.register(CounterSettings)
class CounterSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Browser access', {'fields': ('allowed_origins',)}),
        ('Daily counts', {'fields': ('time_zone',)}),
        ('Visitor IP and location', {'fields': ('trusted_proxy_ips', 'geoip_path')}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # There is only one settings row, so open it directly.
        CounterSettings.objects.get_or_create(pk=1)
        return redirect(reverse('admin:hit_counter_countersettings_change', args=[1]))


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)


@admin.register(Hit)
class HitAdmin(admin.ModelAdmin):
    list_display = (
        'page', 'created_at', 'ip_address', 'country', 'region', 'city', 'location_status',
    )
    list_filter = ('page', 'location_status', 'country')
    search_fields = ('page__code', 'ip_address', 'city')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'page', 'created_at', 'ip_address', 'country', 'region', 'city', 'location_status',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
