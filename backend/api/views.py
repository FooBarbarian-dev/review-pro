"""
Cross-app API views (e.g., dashboard statistics).
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from apps.scans.models import Scan
from apps.findings.models import Finding


class DashboardStatsView(APIView):
    """
    Dashboard statistics endpoint.

    Returns aggregated statistics for the dashboard:
    - Total scans, findings
    - Open findings, false positives
    - Findings by severity, tool, status
    - Recent scans
    - Top vulnerabilities
    """

    def get(self, request):
        """Get dashboard statistics."""

        # Total counts
        total_scans = Scan.objects.count()
        total_findings = Finding.objects.count()
        open_findings = Finding.objects.filter(status='open').count()
        false_positives = Finding.objects.filter(status='false_positive').count()

        # Findings by severity
        findings_by_severity = dict(
            Finding.objects.values('severity').annotate(count=Count('id')).values_list('severity', 'count')
        )

        # Ensure all severities are present
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            if severity not in findings_by_severity:
                findings_by_severity[severity] = 0

        # Findings by tool
        findings_by_tool = dict(
            Finding.objects.values('tool_name').annotate(count=Count('id')).values_list('tool_name', 'count')
        )

        # Scans by status
        scans_by_status = dict(
            Scan.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )

        # Recent scans (last 5)
        recent_scans = Scan.objects.select_related('repository', 'branch').order_by('-created_at')[:5]
        recent_scans_data = [
            {
                'id': str(scan.id),
                'repository': {
                    'id': str(scan.repository.id),
                    'full_name': scan.repository.full_name,
                },
                'branch': scan.branch.name,
                'commit_sha': scan.commit_sha,
                'status': scan.status,
                'total_findings': scan.total_findings,
                'critical_count': scan.critical_count,
                'high_count': scan.high_count,
                'created_at': scan.created_at.isoformat() if scan.created_at else None,
            }
            for scan in recent_scans
        ]

        # Top vulnerabilities (most common rule_ids)
        top_vulnerabilities = (
            Finding.objects
            .values('rule_id', 'severity')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        top_vulnerabilities_data = [
            {
                'rule_id': vuln['rule_id'],
                'severity': vuln['severity'],
                'count': vuln['count'],
            }
            for vuln in top_vulnerabilities
        ]

        return Response({
            'total_scans': total_scans,
            'total_findings': total_findings,
            'open_findings': open_findings,
            'false_positives': false_positives,
            'findings_by_severity': findings_by_severity,
            'findings_by_tool': findings_by_tool,
            'scans_by_status': scans_by_status,
            'recent_scans': recent_scans_data,
            'top_vulnerabilities': top_vulnerabilities_data,
        })
