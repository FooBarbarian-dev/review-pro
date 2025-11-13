"""
Admin configuration for Scan models.
"""
from django.contrib import admin
from .models import Scan, ScanLog, QuotaUsage


class ScanLogInline(admin.TabularInline):
    model = ScanLog
    extra = 0
    fields = ['level', 'message', 'tool', 'timestamp']
    readonly_fields = ['timestamp']
    can_delete = False


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'repository', 'branch', 'commit_sha', 'status',
        'total_findings', 'started_at', 'duration_seconds', 'created_at'
    ]
    list_filter = ['status', 'trigger_type', 'created_at', 'started_at']
    search_fields = ['commit_sha', 'repository__full_name', 'organization__name']
    raw_id_fields = ['organization', 'repository', 'branch', 'triggered_by']
    inlines = [ScanLogInline]
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'started_at', 'completed_at',
        'duration_seconds', 'worker_id', 'worker_container_id'
    ]

    fieldsets = (
        ('Scan Info', {
            'fields': ('id', 'organization', 'repository', 'branch', 'commit_sha', 'status')
        }),
        ('Trigger', {
            'fields': ('triggered_by', 'trigger_type')
        }),
        ('SARIF Storage', {
            'fields': ('sarif_file_path', 'sarif_file_size')
        }),
        ('Statistics', {
            'fields': (
                'total_findings', 'critical_count', 'high_count',
                'medium_count', 'low_count', 'info_count', 'tools_used'
            )
        }),
        ('Worker', {
            'fields': ('worker_id', 'worker_container_id')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
        ('Error', {
            'fields': ('error_message', 'error_details')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ['scan', 'level', 'message_preview', 'tool', 'timestamp']
    list_filter = ['level', 'tool', 'timestamp']
    search_fields = ['message', 'scan__id']
    raw_id_fields = ['scan']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'


@admin.register(QuotaUsage)
class QuotaUsageAdmin(admin.ModelAdmin):
    list_display = ['organization', 'year', 'month', 'scans_used', 'storage_used_gb', 'updated_at']
    list_filter = ['year', 'month', 'organization']
    search_fields = ['organization__name']
    raw_id_fields = ['organization']
    ordering = ['-year', '-month']
    readonly_fields = ['created_at', 'updated_at', 'storage_used_gb']

    def storage_used_gb(self, obj):
        return f"{obj.storage_used_gb:.2f} GB"
    storage_used_gb.short_description = 'Storage Used'
