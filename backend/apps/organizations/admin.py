"""
Admin configuration for Organization models.
"""
from django.contrib import admin
from .models import Organization, OrganizationMembership, Repository, Branch


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 0
    raw_id_fields = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'scan_quota_monthly', 'storage_quota_gb', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'github_org_name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationMembershipInline]
    ordering = ['-created_at']


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__email', 'organization__name']
    raw_id_fields = ['user', 'organization']
    ordering = ['-created_at']


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ['name', 'sha', 'is_default', 'is_protected', 'last_scan_at']


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'organization', 'is_active', 'is_private', 'created_at']
    list_filter = ['is_active', 'is_private', 'created_at']
    search_fields = ['name', 'full_name', 'github_repo_id']
    raw_id_fields = ['organization']
    inlines = [BranchInline]
    ordering = ['-created_at']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['repository', 'name', 'sha', 'is_default', 'is_protected', 'last_scan_at', 'created_at']
    list_filter = ['is_default', 'is_protected', 'created_at']
    search_fields = ['name', 'repository__full_name', 'sha']
    raw_id_fields = ['repository']
    ordering = ['-created_at']
