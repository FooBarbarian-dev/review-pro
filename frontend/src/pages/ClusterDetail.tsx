import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCluster, useClusterFindings } from '../hooks/useApi'
import {
  Card,
  SeverityBadge,
  StatusBadge,
  Loading,
  EmptyState,
} from '../components/ui'
import { ArrowLeft, GitBranch } from 'lucide-react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#2563eb',
  info: '#6b7280',
}

export const ClusterDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { data: cluster, isLoading, error } = useCluster(id!)
  const { data: findings, isLoading: findingsLoading } = useClusterFindings(id!)

  if (isLoading || findingsLoading) {
    return <Loading size="lg" text="Loading cluster details..." />
  }

  if (error || !cluster) {
    return (
      <EmptyState
        title="Cluster not found"
        description="The cluster you're looking for doesn't exist or has been deleted."
      />
    )
  }

  // Prepare scatter plot data
  const scatterData = findings?.map((finding, index) => {
    // Find cluster membership for distance
    const membership = finding.cluster_memberships?.find(
      (m) => m.cluster.id === cluster.id
    )
    return {
      x: index,
      y: membership?.distance_to_centroid || 0,
      severity: finding.severity,
      message: finding.message,
    }
  }) || []

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        to="/clusters"
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to clusters
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <GitBranch className="w-8 h-8 text-gray-400" />
            <h1 className="text-3xl font-bold text-gray-900">
              {cluster.cluster_label}
            </h1>
          </div>
          <p className="mt-2 text-gray-600">
            {cluster.size} semantically similar findings
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div>
            <p className="text-sm text-gray-600">Cluster Size</p>
            <p className="text-2xl font-bold text-gray-900">{cluster.size}</p>
          </div>
        </Card>

        <Card>
          <div>
            <p className="text-sm text-gray-600">Average Similarity</p>
            <p className="text-2xl font-bold text-gray-900">
              {(cluster.avg_similarity * 100).toFixed(1)}%
            </p>
          </div>
        </Card>

        <Card>
          <div>
            <p className="text-sm text-gray-600">Cohesion Score</p>
            <p className="text-2xl font-bold text-gray-900">
              {cluster.cohesion_score.toFixed(3)}
            </p>
          </div>
        </Card>

        <Card>
          <div>
            <p className="text-sm text-gray-600">Algorithm</p>
            <p className="text-2xl font-bold text-gray-900">
              {cluster.algorithm.toUpperCase()}
            </p>
          </div>
        </Card>
      </div>

      {/* Cluster Information */}
      <Card title="Cluster Information">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-gray-600">
              Similarity Threshold
            </dt>
            <dd className="mt-1 text-sm text-gray-900">
              {(cluster.similarity_threshold * 100).toFixed(0)}%
            </dd>
          </div>
          {cluster.primary_tool && (
            <div>
              <dt className="text-sm font-medium text-gray-600">
                Primary Tool
              </dt>
              <dd className="mt-1 text-sm text-gray-900">
                {cluster.primary_tool}
              </dd>
            </div>
          )}
          {cluster.primary_severity && (
            <div>
              <dt className="text-sm font-medium text-gray-600">
                Primary Severity
              </dt>
              <dd className="mt-1">
                <SeverityBadge
                  severity={
                    cluster.primary_severity as
                      | 'critical'
                      | 'high'
                      | 'medium'
                      | 'low'
                      | 'info'
                  }
                />
              </dd>
            </div>
          )}
          {cluster.primary_rule_id && (
            <div>
              <dt className="text-sm font-medium text-gray-600">
                Primary Rule
              </dt>
              <dd className="mt-1 text-sm font-mono text-gray-900">
                {cluster.primary_rule_id}
              </dd>
            </div>
          )}
        </dl>
      </Card>

      {/* Distance Distribution */}
      {scatterData.length > 0 && (
        <Card title="Distance to Centroid Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" name="Finding Index" />
              <YAxis dataKey="y" name="Distance" />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload
                    return (
                      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                        <p className="text-sm font-medium text-gray-900">
                          {data.message}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          Distance: {data.y.toFixed(3)}
                        </p>
                        <SeverityBadge severity={data.severity} className="mt-2" />
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Scatter data={scatterData} fill="#3b82f6">
                {scatterData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      SEVERITY_COLORS[
                        entry.severity as keyof typeof SEVERITY_COLORS
                      ] || SEVERITY_COLORS.info
                    }
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="mt-4 flex items-center gap-4 text-xs text-gray-600">
            <span>Lower distance = more similar to cluster centroid</span>
          </div>
        </Card>
      )}

      {/* Representative Finding */}
      {cluster.representative_finding && (
        <Card title="Representative Finding">
          <Link
            to={`/findings/${cluster.representative_finding.id}`}
            className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <SeverityBadge
                    severity={cluster.representative_finding.severity}
                  />
                  <StatusBadge status={cluster.representative_finding.status} />
                </div>
                <h3 className="mt-2 text-lg font-semibold text-gray-900">
                  {cluster.representative_finding.message}
                </h3>
                <p className="mt-1 text-sm text-gray-600">
                  {cluster.representative_finding.file_path}:
                  {cluster.representative_finding.start_line}
                </p>
              </div>
            </div>
          </Link>
        </Card>
      )}

      {/* Cluster Members */}
      <Card
        title={`Cluster Members (${findings?.length || 0})`}
        action={
          <span className="text-sm text-gray-600">
            Sorted by distance to centroid
          </span>
        }
      >
        {!findings || findings.length === 0 ? (
          <p className="text-sm text-gray-600">No findings in this cluster</p>
        ) : (
          <div className="space-y-3">
            {findings.map((finding) => {
              const membership = finding.cluster_memberships?.find(
                (m) => m.cluster.id === cluster.id
              )
              return (
                <Link
                  key={finding.id}
                  to={`/findings/${finding.id}`}
                  className="block p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
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
                      <p className="mt-2 font-medium text-gray-900">
                        {finding.message}
                      </p>
                      <p className="mt-1 text-sm text-gray-600">
                        {finding.file_path}:{finding.start_line}
                      </p>
                    </div>
                    {membership && (
                      <div className="text-right ml-4">
                        <p className="text-xs text-gray-600">Distance</p>
                        <p className="text-sm font-medium text-gray-900">
                          {membership.distance_to_centroid.toFixed(3)}
                        </p>
                      </div>
                    )}
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
