import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useFindings } from '../hooks/useApi'
import {
  Card,
  SeverityBadge,
  StatusBadge,
  Loading,
  EmptyState,
} from '../components/ui'
import { AlertTriangle } from 'lucide-react'

export const Findings: React.FC = () => {
  const [searchParams] = useSearchParams()
  const scanId = searchParams.get('scan_id') || undefined

  const [filters, setFilters] = useState({
    severity: '',
    status: '',
    tool_name: '',
  })

  const { data, isLoading, error } = useFindings({
    scan_id: scanId,
    severity: filters.severity || undefined,
    status: filters.status || undefined,
    tool_name: filters.tool_name || undefined,
  })

  if (isLoading) {
    return <Loading size="lg" text="Loading findings..." />
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load findings"
        description="There was an error loading the findings."
      />
    )
  }

  const findings = data?.results || []

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Findings</h1>
        <p className="mt-2 text-gray-600">
          Security vulnerabilities detected across scans
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity
            </label>
            <select
              value={filters.severity}
              onChange={(e) =>
                setFilters({ ...filters, severity: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="fixed">Fixed</option>
              <option value="false_positive">False Positive</option>
              <option value="accepted_risk">Accepted Risk</option>
              <option value="wont_fix">Won't Fix</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tool
            </label>
            <select
              value={filters.tool_name}
              onChange={(e) =>
                setFilters({ ...filters, tool_name: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All</option>
              <option value="semgrep">Semgrep</option>
              <option value="bandit">Bandit</option>
              <option value="ruff">Ruff</option>
            </select>
          </div>
        </div>
        <div className="mt-4 text-sm text-gray-600">
          {data?.count || 0} total findings
        </div>
      </Card>

      {/* Findings List */}
      {findings.length === 0 ? (
        <EmptyState
          title="No findings found"
          description="No security vulnerabilities match your current filters."
          icon={<AlertTriangle className="w-16 h-16" />}
        />
      ) : (
        <div className="space-y-4">
          {findings.map((finding) => (
            <Card key={finding.id}>
              <Link
                to={`/findings/${finding.id}`}
                className="block hover:bg-gray-50 -m-6 p-6 rounded-lg transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <SeverityBadge severity={finding.severity} />
                      <StatusBadge status={finding.status} />
                      <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded">
                        {finding.tool_name}
                      </span>
                    </div>
                    <h3 className="mt-2 text-lg font-semibold text-gray-900">
                      {finding.message}
                    </h3>
                    <div className="mt-2 space-y-1">
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">File:</span>{' '}
                        {finding.file_path}:{finding.start_line}
                      </p>
                      {finding.rule_name && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Rule:</span>{' '}
                          {finding.rule_name}
                        </p>
                      )}
                      {finding.cwe_ids.length > 0 && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">CWE:</span>{' '}
                          {finding.cwe_ids.join(', ')}
                        </p>
                      )}
                    </div>

                    {/* Code Snippet */}
                    {finding.snippet && (
                      <div className="mt-3">
                        <pre className="p-3 text-xs bg-gray-900 text-gray-100 rounded-lg overflow-x-auto">
                          <code>{finding.snippet}</code>
                        </pre>
                      </div>
                    )}

                    {/* LLM Verdicts */}
                    {finding.llm_verdicts && finding.llm_verdicts.length > 0 && (
                      <div className="mt-3 flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700">
                          LLM Analysis:
                        </span>
                        {finding.llm_verdicts.map((verdict) => (
                          <span
                            key={verdict.id}
                            className={`px-2 py-1 text-xs font-medium rounded ${
                              verdict.verdict === 'true_positive'
                                ? 'bg-red-100 text-red-800'
                                : verdict.verdict === 'false_positive'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {verdict.verdict.replace(/_/g, ' ').toUpperCase()} (
                            {(verdict.confidence * 100).toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Cluster Membership */}
                    {finding.cluster_memberships &&
                      finding.cluster_memberships.length > 0 && (
                        <div className="mt-2 text-sm text-gray-600">
                          <span className="font-medium">Cluster:</span>{' '}
                          {finding.cluster_memberships[0].cluster.cluster_label}
                        </div>
                      )}

                    {/* Occurrence Count */}
                    {finding.occurrence_count > 1 && (
                      <div className="mt-2 text-sm text-gray-600">
                        <span className="font-medium">Occurrences:</span>{' '}
                        {finding.occurrence_count}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
