import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useFinding, useUpdateFindingStatus } from '../hooks/useApi'
import {
  Card,
  SeverityBadge,
  StatusBadge,
  Loading,
  EmptyState,
  Button,
} from '../components/ui'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export const FindingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { data: finding, isLoading, error } = useFinding(id!)
  const updateStatusMutation = useUpdateFindingStatus()
  const [selectedStatus, setSelectedStatus] = useState('')

  if (isLoading) {
    return <Loading size="lg" text="Loading finding details..." />
  }

  if (error || !finding) {
    return (
      <EmptyState
        title="Finding not found"
        description="The finding you're looking for doesn't exist or has been deleted."
      />
    )
  }

  const handleStatusChange = () => {
    if (selectedStatus && selectedStatus !== finding.status) {
      updateStatusMutation.mutate({ id: finding.id, status: selectedStatus })
    }
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        to="/findings"
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to findings
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <SeverityBadge severity={finding.severity} />
            <StatusBadge status={finding.status} />
            <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded">
              {finding.tool_name}
            </span>
          </div>
          <h1 className="mt-3 text-3xl font-bold text-gray-900">
            {finding.message}
          </h1>
        </div>
      </div>

      {/* Status Update */}
      <Card title="Update Status">
        <div className="flex items-center gap-3">
          <select
            value={selectedStatus || finding.status}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="open">Open</option>
            <option value="fixed">Fixed</option>
            <option value="false_positive">False Positive</option>
            <option value="accepted_risk">Accepted Risk</option>
            <option value="wont_fix">Won't Fix</option>
          </select>
          <Button
            variant="primary"
            onClick={handleStatusChange}
            loading={updateStatusMutation.isPending}
            disabled={!selectedStatus || selectedStatus === finding.status}
          >
            Update Status
          </Button>
        </div>
      </Card>

      {/* Details */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Finding Details">
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-medium text-gray-600">Severity</dt>
              <dd className="mt-1">
                <SeverityBadge severity={finding.severity} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Status</dt>
              <dd className="mt-1">
                <StatusBadge status={finding.status} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Tool</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {finding.tool_name}
                {finding.tool_version && ` v${finding.tool_version}`}
              </dd>
            </div>
            {finding.rule_id && (
              <div>
                <dt className="text-sm font-medium text-gray-600">Rule ID</dt>
                <dd className="mt-1 text-sm font-mono text-gray-900">
                  {finding.rule_id}
                </dd>
              </div>
            )}
            {finding.rule_name && (
              <div>
                <dt className="text-sm font-medium text-gray-600">Rule Name</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {finding.rule_name}
                </dd>
              </div>
            )}
            {finding.cwe_ids.length > 0 && (
              <div>
                <dt className="text-sm font-medium text-gray-600">CWE IDs</dt>
                <dd className="flex flex-wrap gap-2 mt-1">
                  {finding.cwe_ids.map((cwe) => (
                    <a
                      key={cwe}
                      href={`https://cwe.mitre.org/data/definitions/${cwe.replace(
                        'CWE-',
                        ''
                      )}.html`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200"
                    >
                      {cwe}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </Card>

        <Card title="Location">
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-medium text-gray-600">File Path</dt>
              <dd className="mt-1 text-sm font-mono text-gray-900">
                {finding.file_path}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Line</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {finding.start_line}
                {finding.end_line && finding.end_line !== finding.start_line
                  ? `-${finding.end_line}`
                  : ''}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Column</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {finding.start_column}
                {finding.end_column && finding.end_column !== finding.start_column
                  ? `-${finding.end_column}`
                  : ''}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">First Seen</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {formatDistanceToNow(new Date(finding.first_seen_at), {
                  addSuffix: true,
                })}
              </dd>
            </div>
            {finding.occurrence_count > 1 && (
              <div>
                <dt className="text-sm font-medium text-gray-600">
                  Occurrences
                </dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {finding.occurrence_count}
                </dd>
              </div>
            )}
          </dl>
        </Card>
      </div>

      {/* Code Snippet */}
      {finding.snippet && (
        <Card title="Code Snippet">
          <pre className="p-4 text-sm bg-gray-900 text-gray-100 rounded-lg overflow-x-auto">
            <code>{finding.snippet}</code>
          </pre>
        </Card>
      )}

      {/* LLM Verdicts */}
      {finding.llm_verdicts && finding.llm_verdicts.length > 0 && (
        <Card title="LLM Analysis">
          <div className="space-y-4">
            {finding.llm_verdicts.map((verdict) => (
              <div
                key={verdict.id}
                className="p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span
                        className={`px-3 py-1 text-sm font-medium rounded ${
                          verdict.verdict === 'true_positive'
                            ? 'bg-red-100 text-red-800'
                            : verdict.verdict === 'false_positive'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {verdict.verdict.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-600">
                        Confidence: {(verdict.confidence * 100).toFixed(0)}%
                      </span>
                      <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded">
                        {verdict.agent_pattern.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="mt-3">
                      <h4 className="text-sm font-medium text-gray-900">
                        Reasoning:
                      </h4>
                      <p className="mt-1 text-sm text-gray-700">
                        {verdict.reasoning}
                      </p>
                    </div>
                    {verdict.recommendation && (
                      <div className="mt-3">
                        <h4 className="text-sm font-medium text-gray-900">
                          Recommendation:
                        </h4>
                        <p className="mt-1 text-sm text-gray-700">
                          {verdict.recommendation}
                        </p>
                      </div>
                    )}
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-600">
                      <span>
                        Model: {verdict.llm_provider}/{verdict.llm_model}
                      </span>
                      <span>Tokens: {verdict.total_tokens}</span>
                      <span>Cost: ${verdict.estimated_cost_usd}</span>
                      <span>Time: {verdict.processing_time_ms}ms</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Cluster Membership */}
      {finding.cluster_memberships &&
        finding.cluster_memberships.length > 0 && (
          <Card title="Cluster Membership">
            <div className="space-y-3">
              {finding.cluster_memberships.map((membership) => (
                <Link
                  key={membership.id}
                  to={`/clusters/${membership.cluster.id}`}
                  className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {membership.cluster.cluster_label}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {membership.cluster.size} findings •{' '}
                        {membership.cluster.algorithm} clustering
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">
                        Distance to centroid
                      </p>
                      <p className="font-medium text-gray-900">
                        {membership.distance_to_centroid.toFixed(3)}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </Card>
        )}
    </div>
  )
}
