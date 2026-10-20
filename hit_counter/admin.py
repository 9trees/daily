from django.contrib import admin

from .models import Hit, Page


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
