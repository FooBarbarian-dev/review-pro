-- Row-Level Security (RLS) policies for multi-tenancy enforcement (ADR-001)
--
-- This script implements database-level multi-tenancy isolation using PostgreSQL RLS.
-- RLS provides defense-in-depth by enforcing access control at the database layer,
-- preventing data leakage even if application-level filtering fails.
--
-- USAGE:
--   Run this after initial migrations:
--   psql -U postgres -d secanalysis -f row_level_security.sql
--
-- OR apply via Django migration (see: 0002_row_level_security.py)
--
-- IMPORTANT:
--   RLS requires setting current_user_id in session for policy enforcement.
--   Application must call SET SESSION app.current_user_id = '<user_uuid>'
--   before queries.

-- ============================================================================
-- CONFIGURATION
-- ============================================================================

-- Create schema for RLS helper functions
CREATE SCHEMA IF NOT EXISTS rls;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get current user ID from session variable
CREATE OR REPLACE FUNCTION rls.current_user_id()
RETURNS UUID AS $$
BEGIN
    RETURN current_setting('app.current_user_id', true)::uuid;
EXCEPTION
    WHEN OTHERS THEN
        -- Return NULL if setting not found or invalid
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION rls.current_user_id() IS
'Get current user UUID from session variable app.current_user_id';


-- Function to check if current user is superuser
CREATE OR REPLACE FUNCTION rls.is_superuser()
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if user is PostgreSQL superuser (bypass all RLS)
    RETURN (SELECT usesuper FROM pg_user WHERE usename = current_user);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION rls.is_superuser() IS
'Check if current database user is a superuser (for RLS bypass)';


-- Function to get user's organization IDs
CREATE OR REPLACE FUNCTION rls.user_organizations()
RETURNS TABLE(organization_id UUID) AS $$
BEGIN
    RETURN QUERY
    SELECT om.organization_id
    FROM organization_memberships om
    WHERE om.user_id = rls.current_user_id();
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION rls.user_organizations() IS
'Get all organization IDs that current user is a member of';

-- ============================================================================
-- ROW-LEVEL SECURITY POLICIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- ORGANIZATIONS TABLE
-- ----------------------------------------------------------------------------

-- Enable RLS on organizations
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see organizations they are members of
CREATE POLICY org_select_policy ON organizations
    FOR SELECT
    USING (
        rls.is_superuser() OR  -- Superusers see all
        id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Users can update organizations where they are owners/admins
CREATE POLICY org_update_policy ON organizations
    FOR UPDATE
    USING (
        rls.is_superuser() OR
        id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin')
        )
    );

-- Policy: Users can insert organizations (becomes owner automatically)
CREATE POLICY org_insert_policy ON organizations
    FOR INSERT
    WITH CHECK (true);  -- Application handles owner creation

-- Policy: Only owners can delete organizations
CREATE POLICY org_delete_policy ON organizations
    FOR DELETE
    USING (
        rls.is_superuser() OR
        id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role = 'owner'
        )
    );

COMMENT ON POLICY org_select_policy ON organizations IS
'Users can only view organizations they are members of';

-- ----------------------------------------------------------------------------
-- ORGANIZATION_MEMBERSHIPS TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see memberships for their organizations
CREATE POLICY membership_select_policy ON organization_memberships
    FOR SELECT
    USING (
        rls.is_superuser() OR
        organization_id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Admins/owners can manage memberships
CREATE POLICY membership_modify_policy ON organization_memberships
    FOR ALL
    USING (
        rls.is_superuser() OR
        organization_id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin')
        )
    );

-- ----------------------------------------------------------------------------
-- REPOSITORIES TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see repositories in their organizations
CREATE POLICY repository_select_policy ON repositories
    FOR SELECT
    USING (
        rls.is_superuser() OR
        organization_id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Members can create/update repositories
CREATE POLICY repository_modify_policy ON repositories
    FOR ALL
    USING (
        rls.is_superuser() OR
        organization_id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin', 'member')
        )
    );

-- ----------------------------------------------------------------------------
-- BRANCHES TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE branches ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see branches for repositories in their organizations
CREATE POLICY branch_select_policy ON branches
    FOR SELECT
    USING (
        rls.is_superuser() OR
        repository_id IN (
            SELECT r.id
            FROM repositories r
            WHERE r.organization_id IN (SELECT organization_id FROM rls.user_organizations())
        )
    );

-- Policy: Members can manage branches
CREATE POLICY branch_modify_policy ON branches
    FOR ALL
    USING (
        rls.is_superuser() OR
        repository_id IN (
            SELECT r.id
            FROM repositories r
            WHERE r.organization_id IN (
                SELECT om.organization_id
                FROM organization_memberships om
                WHERE om.user_id = rls.current_user_id()
                AND om.role IN ('owner', 'admin', 'member')
            )
        )
    );

-- ----------------------------------------------------------------------------
-- SCANS TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see scans for their organizations
CREATE POLICY scan_select_policy ON scans
    FOR SELECT
    USING (
        rls.is_superuser() OR
        organization_id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Members can create/cancel scans
CREATE POLICY scan_modify_policy ON scans
    FOR ALL
    USING (
        rls.is_superuser() OR
        organization_id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin', 'member')
        )
    );

-- ----------------------------------------------------------------------------
-- SCAN_LOGS TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE scan_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see logs for scans in their organizations
CREATE POLICY scan_log_policy ON scan_logs
    FOR SELECT
    USING (
        rls.is_superuser() OR
        scan_id IN (
            SELECT s.id
            FROM scans s
            WHERE s.organization_id IN (SELECT organization_id FROM rls.user_organizations())
        )
    );

-- ----------------------------------------------------------------------------
-- QUOTA_USAGE TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE quota_usage ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see quota for their organizations
CREATE POLICY quota_select_policy ON quota_usage
    FOR SELECT
    USING (
        rls.is_superuser() OR
        organization_id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Only system/admins can update quota
CREATE POLICY quota_update_policy ON quota_usage
    FOR ALL
    USING (
        rls.is_superuser() OR
        organization_id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin')
        )
    );

-- ----------------------------------------------------------------------------
-- FINDINGS TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see findings for their organizations
CREATE POLICY finding_select_policy ON findings
    FOR SELECT
    USING (
        rls.is_superuser() OR
        organization_id IN (SELECT organization_id FROM rls.user_organizations())
    );

-- Policy: Members can update finding status
CREATE POLICY finding_modify_policy ON findings
    FOR ALL
    USING (
        rls.is_superuser() OR
        organization_id IN (
            SELECT om.organization_id
            FROM organization_memberships om
            WHERE om.user_id = rls.current_user_id()
            AND om.role IN ('owner', 'admin', 'member')
        )
    );

-- ----------------------------------------------------------------------------
-- FINDING_COMMENTS TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE finding_comments ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see comments on findings in their organizations
CREATE POLICY finding_comment_policy ON finding_comments
    FOR ALL
    USING (
        rls.is_superuser() OR
        finding_id IN (
            SELECT f.id
            FROM findings f
            WHERE f.organization_id IN (SELECT organization_id FROM rls.user_organizations())
        )
    );

-- ----------------------------------------------------------------------------
-- FINDING_STATUS_HISTORY TABLE
-- ----------------------------------------------------------------------------

ALTER TABLE finding_status_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see status history for findings in their organizations
CREATE POLICY finding_history_policy ON finding_status_history
    FOR SELECT
    USING (
        rls.is_superuser() OR
        finding_id IN (
            SELECT f.id
            FROM findings f
            WHERE f.organization_id IN (SELECT organization_id FROM rls.user_organizations())
        )
    );

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant usage on rls schema
GRANT USAGE ON SCHEMA rls TO PUBLIC;

-- Grant execute on helper functions
GRANT EXECUTE ON FUNCTION rls.current_user_id() TO PUBLIC;
GRANT EXECUTE ON FUNCTION rls.is_superuser() TO PUBLIC;
GRANT EXECUTE ON FUNCTION rls.user_organizations() TO PUBLIC;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify RLS is enabled on all tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = true
ORDER BY tablename;

-- Verify policies are created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================

-- To use RLS in Django views, set the session variable before queries:
--
-- from django.db import connection
--
-- def set_rls_context(user_id):
--     with connection.cursor() as cursor:
--         cursor.execute(f"SET SESSION app.current_user_id = %s", [str(user_id)])
--
-- def clear_rls_context():
--     with connection.cursor() as cursor:
--         cursor.execute("RESET app.current_user_id")
--
-- Usage in view:
--
-- def my_view(request):
--     set_rls_context(request.user.id)
--     try:
--         # All queries now filtered by RLS
--         orgs = Organization.objects.all()
--         return Response(...)
--     finally:
--         clear_rls_context()

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- To remove RLS policies:
-- DROP POLICY IF EXISTS org_select_policy ON organizations;
-- DROP POLICY IF EXISTS org_update_policy ON organizations;
-- ... (repeat for all policies)
-- ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
-- ... (repeat for all tables)
-- DROP SCHEMA IF EXISTS rls CASCADE;
