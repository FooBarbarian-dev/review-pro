"""
Admin configuration for Finding models.
"""
from django.contrib import admin
from .models import Finding, FindingComment, FindingStatusHistory


class FindingCommentInline(admin.TabularInline):
    model = FindingComment
    extra = 0
    fields = ['author', 'content', 'created_at']
    readonly_fields = ['created_at']


class FindingStatusHistoryInline(admin.TabularInline):
    model = FindingStatusHistory
    extra = 0
    fields = ['changed_by', 'old_status', 'new_status', 'reason', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = [
        'rule_id', 'file_path', 'start_line', 'severity', 'status',
        'tool_name', 'occurrence_count', 'first_seen_at', 'last_seen_at'
    ]
    list_filter = ['severity', 'status', 'tool_name', 'first_seen_at']
    search_fields = [
        'rule_id', 'rule_name', 'message', 'file_path',
        'repository__full_name', 'organization__name'
    ]
    raw_id_fields = ['organization', 'repository', 'first_seen_scan', 'last_seen_scan']
    inlines = [FindingCommentInline, FindingStatusHistoryInline]
    ordering = ['-severity', '-first_seen_at']
    readonly_fields = [
        'fingerprint', 'occurrence_count', 'first_seen_at',
        'last_seen_at', 'fixed_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Finding Info', {
            'fields': (
                'organization', 'repository', 'fingerprint', 'rule_id',
                'rule_name', 'message', 'severity', 'status'
            )
        }),
        ('Location', {
            'fields': (
                'file_path', 'start_line', 'start_column',
                'end_line', 'end_column', 'snippet'
            )
        }),
        ('Tool', {
            'fields': ('tool_name', 'tool_version')
        }),
        ('Security Info', {
            'fields': ('cwe_ids', 'cve_ids')
        }),
        ('Tracking', {
            'fields': (
                'first_seen_scan', 'last_seen_scan', 'occurrence_count',
                'first_seen_at', 'last_seen_at', 'fixed_at'
            )
        }),
        ('SARIF Data', {
            'fields': ('sarif_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(FindingComment)
class FindingCommentAdmin(admin.ModelAdmin):
    list_display = ['finding', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__email', 'finding__rule_id']
    raw_id_fields = ['finding', 'author']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(FindingStatusHistory)
class FindingStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['finding', 'changed_by', 'old_status', 'new_status', 'created_at']
    list_filter = ['old_status', 'new_status', 'created_at']
    search_fields = ['finding__rule_id', 'changed_by__email', 'reason']
    raw_id_fields = ['finding', 'changed_by']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
