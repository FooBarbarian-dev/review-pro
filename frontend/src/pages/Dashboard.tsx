import React from 'react'
import { Link } from 'react-router-dom'
import { useDashboardStats } from '../hooks/useApi'
import { Card, SeverityBadge, StatusBadge, Loading, EmptyState } from '../components/ui'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { FileSearch, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

const COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#2563eb',
  info: '#6b7280',
}

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading, error } = useDashboardStats()

  if (isLoading) {
    return <Loading size="lg" text="Loading dashboard..." />
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load dashboard"
        description="There was an error loading the dashboard statistics."
        icon={<XCircle className="w-16 h-16" />}
      />
    )
  }

  if (!stats) {
    return (
      <EmptyState
        title="No data available"
        description="Start scanning repositories to see statistics."
        icon={<FileSearch className="w-16 h-16" />}
      />
    )
  }

  // Prepare chart data
  const severityData = Object.entries(stats.findings_by_severity).map(
    ([severity, count]) => ({
      name: severity.charAt(0).toUpperCase() + severity.slice(1),
      value: count,
      color: COLORS[severity as keyof typeof COLORS] || COLORS.info,
    })
  )

  const toolData = Object.entries(stats.findings_by_tool).map(
    ([tool, count]) => ({
      name: tool,
      findings: count,
    })
  )

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of security scans and findings
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg">
              <FileSearch className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Scans</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.total_scans}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Findings</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.total_findings}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Open Findings</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.open_findings}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">False Positives</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.false_positives}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Findings by Severity */}
        <Card title="Findings by Severity">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Findings by Tool */}
        <Card title="Findings by Tool">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={toolData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="findings" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Recent Scans and Top Vulnerabilities */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Scans */}
        <Card
          title="Recent Scans"
          action={
            <Link
              to="/scans"
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              View all
            </Link>
          }
        >
          {stats.recent_scans.length === 0 ? (
            <p className="text-sm text-gray-600">No scans yet</p>
          ) : (
            <div className="space-y-3">
              {stats.recent_scans.slice(0, 5).map((scan) => (
                <Link
                  key={scan.id}
                  to={`/scans/${scan.id}`}
                  className="block p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {scan.repository.full_name}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {scan.branch} • {scan.commit_sha.slice(0, 7)}
                      </p>
                    </div>
                    <StatusBadge status={scan.status} />
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-gray-600">
                      {scan.total_findings} findings
                    </span>
                    {scan.critical_count > 0 && (
                      <SeverityBadge severity="critical" />
                    )}
                    {scan.high_count > 0 && (
                      <SeverityBadge severity="high" />
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        {/* Top Vulnerabilities */}
        <Card
          title="Top Vulnerabilities"
          action={
            <Link
              to="/findings"
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              View all
            </Link>
          }
        >
          {stats.top_vulnerabilities.length === 0 ? (
            <p className="text-sm text-gray-600">No vulnerabilities found</p>
          ) : (
            <div className="space-y-3">
              {stats.top_vulnerabilities.slice(0, 5).map((vuln) => (
                <div
                  key={vuln.rule_id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {vuln.rule_id}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <SeverityBadge
                        severity={
                          vuln.severity as
                            | 'critical'
                            | 'high'
                            | 'medium'
                            | 'low'
                            | 'info'
                        }
                      />
                      <span className="text-xs text-gray-600">
                        {vuln.count} occurrences
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
