import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  useScan,
  useFindings,
  useTriggerRescan,
  useTriggerAdjudication,
  useTriggerClustering,
} from '../hooks/useApi'
import {
  Card,
  SeverityBadge,
  StatusBadge,
  Loading,
  EmptyState,
  Button,
} from '../components/ui'
import {
  ArrowLeft,
  RefreshCw,
  Brain,
  GitBranch,
  Clock,
  CheckCircle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export const ScanDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { data: scan, isLoading, error } = useScan(id!)
  const { data: findingsData } = useFindings({ scan_id: id })
  const rescanMutation = useTriggerRescan()
  const adjudicationMutation = useTriggerAdjudication()
  const clusteringMutation = useTriggerClustering()
  const [selectedPattern, setSelectedPattern] = useState('post_processing')

  if (isLoading) {
    return <Loading size="lg" text="Loading scan details..." />
  }

  if (error || !scan) {
    return (
      <EmptyState
        title="Scan not found"
        description="The scan you're looking for doesn't exist or has been deleted."
      />
    )
  }

  const findings = findingsData?.results || []

  const handleRescan = () => {
    rescanMutation.mutate(scan.id)
  }

  const handleAdjudicate = () => {
    adjudicationMutation.mutate({
      scanId: scan.id,
      pattern: selectedPattern,
    })
  }

  const handleCluster = () => {
    clusteringMutation.mutate({
      scanId: scan.id,
    })
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        to="/scans"
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to scans
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {scan.repository.full_name}
          </h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
            <span>
              <span className="font-medium">Branch:</span> {scan.branch}
            </span>
            <span>
              <span className="font-medium">Commit:</span>{' '}
              {scan.commit_sha.slice(0, 7)}
            </span>
            <span>
              {formatDistanceToNow(new Date(scan.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>
        </div>
        <StatusBadge status={scan.status} />
      </div>

      {/* Actions */}
      <Card>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={handleRescan}
            loading={rescanMutation.isPending}
          >
            <RefreshCw className="w-4 h-4" />
            Re-scan
          </Button>

          <div className="flex items-center gap-2">
            <select
              value={selectedPattern}
              onChange={(e) => setSelectedPattern(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="post_processing">Post-Processing Filter</option>
              <option value="interactive">Interactive Retrieval</option>
              <option value="multi_agent">Multi-Agent</option>
            </select>
            <Button
              variant="primary"
              onClick={handleAdjudicate}
              loading={adjudicationMutation.isPending}
            >
              <Brain className="w-4 h-4" />
              Run LLM Adjudication
            </Button>
          </div>

          <Button
            variant="secondary"
            onClick={handleCluster}
            loading={clusteringMutation.isPending}
          >
            <GitBranch className="w-4 h-4" />
            Cluster Findings
          </Button>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-gray-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Findings</p>
              <p className="text-2xl font-bold text-gray-900">
                {scan.total_findings}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-lg">
              <SeverityBadge severity="critical" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Critical</p>
              <p className="text-2xl font-bold text-red-600">
                {scan.critical_count}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-orange-100 rounded-lg">
              <SeverityBadge severity="high" />
            </div>
            <div>
              <p className="text-sm text-gray-600">High</p>
              <p className="text-2xl font-bold text-orange-600">
                {scan.high_count}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg">
              <SeverityBadge severity="medium" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Medium</p>
              <p className="text-2xl font-bold text-yellow-600">
                {scan.medium_count}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Details */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Scan Information">
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-medium text-gray-600">Status</dt>
              <dd className="mt-1">
                <StatusBadge status={scan.status} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Tools Used</dt>
              <dd className="flex gap-2 mt-1">
                {scan.tools_used.map((tool) => (
                  <span
                    key={tool}
                    className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded"
                  >
                    {tool}
                  </span>
                ))}
              </dd>
            </div>
            {scan.started_at && (
              <div>
                <dt className="text-sm font-medium text-gray-600">Started</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(scan.started_at).toLocaleString()}
                </dd>
              </div>
            )}
            {scan.completed_at && (
              <div>
                <dt className="text-sm font-medium text-gray-600">Completed</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(scan.completed_at).toLocaleString()}
                </dd>
              </div>
            )}
            {scan.duration_seconds && (
              <div>
                <dt className="text-sm font-medium text-gray-600">Duration</dt>
                <dd className="flex items-center gap-2 mt-1 text-sm text-gray-900">
                  <Clock className="w-4 h-4" />
                  {scan.duration_seconds}s
                </dd>
              </div>
            )}
          </dl>
        </Card>

        <Card title="Repository Information">
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-medium text-gray-600">Name</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {scan.repository.full_name}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Branch</dt>
              <dd className="mt-1 text-sm text-gray-900">{scan.branch}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600">Commit</dt>
              <dd className="mt-1 text-sm font-mono text-gray-900">
                {scan.commit_sha}
              </dd>
            </div>
          </dl>
        </Card>
      </div>

      {/* Findings List */}
      <Card
        title="Findings"
        action={
          findings.length > 0 && (
            <Link
              to={`/findings?scan_id=${scan.id}`}
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              View all findings
            </Link>
          )
        }
      >
        {findings.length === 0 ? (
          <p className="text-sm text-gray-600">No findings for this scan</p>
        ) : (
          <div className="space-y-3">
            {findings.slice(0, 10).map((finding) => (
              <Link
                key={finding.id}
                to={`/findings/${finding.id}`}
                className="block p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={finding.severity} />
                      <p className="font-medium text-gray-900 truncate">
                        {finding.message}
                      </p>
                    </div>
                    <p className="mt-1 text-xs text-gray-600">
                      {finding.file_path}:{finding.start_line}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
            {findings.length > 10 && (
              <Link
                to={`/findings?scan_id=${scan.id}`}
                className="block text-sm text-center text-primary-600 hover:text-primary-700"
              >
                View {findings.length - 10} more findings
              </Link>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
