import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useClusters } from '../hooks/useApi'
import { Card, SeverityBadge, Loading, EmptyState } from '../components/ui'
import { GitBranch } from 'lucide-react'

export const Clusters: React.FC = () => {
  const [searchParams] = useSearchParams()
  const scanId = searchParams.get('scan_id') || undefined

  const [minSize, setMinSize] = useState<number>(2)

  const { data, isLoading, error } = useClusters({
    scan_id: scanId,
    min_size: minSize,
  })

  if (isLoading) {
    return <Loading size="lg" text="Loading clusters..." />
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load clusters"
        description="There was an error loading the clusters."
      />
    )
  }

  const clusters = data?.results || []

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Finding Clusters</h1>
        <p className="mt-2 text-gray-600">
          Semantically similar findings grouped together
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">
            Minimum cluster size:
          </label>
          <input
            type="number"
            min="1"
            value={minSize}
            onChange={(e) => setMinSize(parseInt(e.target.value) || 1)}
            className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <span className="text-sm text-gray-600">
            {data?.count || 0} total clusters
          </span>
        </div>
      </Card>

      {/* Clusters List */}
      {clusters.length === 0 ? (
        <EmptyState
          title="No clusters found"
          description="Run clustering on your scans to group similar findings."
          icon={<GitBranch className="w-16 h-16" />}
        />
      ) : (
        <div className="space-y-4">
          {clusters.map((cluster) => (
            <Card key={cluster.id}>
              <Link
                to={`/clusters/${cluster.id}`}
                className="block hover:bg-gray-50 -m-6 p-6 rounded-lg transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <GitBranch className="w-5 h-5 text-gray-400" />
                      <h3 className="text-lg font-semibold text-gray-900">
                        {cluster.cluster_label}
                      </h3>
                      <span className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded">
                        {cluster.size} findings
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mt-4 sm:grid-cols-4">
                      <div>
                        <p className="text-sm text-gray-600">Algorithm</p>
                        <p className="text-sm font-medium text-gray-900">
                          {cluster.algorithm.toUpperCase()}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Avg Similarity</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(cluster.avg_similarity * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Cohesion Score</p>
                        <p className="text-sm font-medium text-gray-900">
                          {cluster.cohesion_score.toFixed(3)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Threshold</p>
                        <p className="text-sm font-medium text-gray-900">
                          {(cluster.similarity_threshold * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>

                    {cluster.representative_finding && (
                      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs font-medium text-gray-600 mb-2">
                          Representative Finding:
                        </p>
                        <div className="flex items-center gap-2">
                          <SeverityBadge
                            severity={cluster.representative_finding.severity}
                          />
                          <p className="text-sm text-gray-900">
                            {cluster.representative_finding.message}
                          </p>
                        </div>
                        <p className="mt-1 text-xs text-gray-600">
                          {cluster.representative_finding.file_path}:
                          {cluster.representative_finding.start_line}
                        </p>
                      </div>
                    )}

                    <div className="flex items-center gap-4 mt-4 text-sm text-gray-600">
                      {cluster.primary_tool && (
                        <span>
                          <span className="font-medium">Tool:</span>{' '}
                          {cluster.primary_tool}
                        </span>
                      )}
                      {cluster.primary_severity && (
                        <span>
                          <span className="font-medium">Severity:</span>{' '}
                          {cluster.primary_severity}
                        </span>
                      )}
                      {cluster.primary_rule_id && (
                        <span>
                          <span className="font-medium">Rule:</span>{' '}
                          {cluster.primary_rule_id}
                        </span>
                      )}
                    </div>
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
