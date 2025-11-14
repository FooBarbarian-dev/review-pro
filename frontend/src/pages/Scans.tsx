import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useScans } from '../hooks/useApi'
import {
  Card,
  StatusBadge,
  Loading,
  EmptyState,
  Button,
} from '../components/ui'
import { FileSearch, Plus } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export const Scans: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const { data, isLoading, error } = useScans(
    statusFilter ? { status: statusFilter } : undefined
  )

  if (isLoading) {
    return <Loading size="lg" text="Loading scans..." />
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load scans"
        description="There was an error loading the scans."
      />
    )
  }

  const scans = data?.results || []

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Scans</h1>
          <p className="mt-2 text-gray-600">
            Security scans across your repositories
          </p>
        </div>
        <Button variant="primary">
          <Plus className="w-4 h-4" />
          New Scan
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <span className="text-sm text-gray-600">
            {data?.count || 0} total scans
          </span>
        </div>
      </Card>

      {/* Scans List */}
      {scans.length === 0 ? (
        <EmptyState
          title="No scans found"
          description="Start scanning your repositories to find security vulnerabilities."
          icon={<FileSearch className="w-16 h-16" />}
          action={
            <Button variant="primary">
              <Plus className="w-4 h-4" />
              Create Your First Scan
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {scans.map((scan) => (
            <Card key={scan.id}>
              <Link
                to={`/scans/${scan.id}`}
                className="block hover:bg-gray-50 -m-6 p-6 rounded-lg transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {scan.repository.full_name}
                      </h3>
                      <StatusBadge status={scan.status} />
                    </div>
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
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mt-4 sm:grid-cols-4">
                  <div>
                    <p className="text-sm text-gray-600">Total Findings</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {scan.total_findings}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Critical</p>
                    <p className="text-2xl font-bold text-red-600">
                      {scan.critical_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">High</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {scan.high_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Medium</p>
                    <p className="text-2xl font-bold text-yellow-600">
                      {scan.medium_count}
                    </p>
                  </div>
                </div>

                {/* Tools */}
                <div className="flex items-center gap-2 mt-4">
                  <span className="text-sm text-gray-600">Tools:</span>
                  {scan.tools_used.map((tool) => (
                    <span
                      key={tool}
                      className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded"
                    >
                      {tool}
                    </span>
                  ))}
                </div>

                {/* Duration */}
                {scan.duration_seconds && (
                  <div className="mt-2 text-sm text-gray-600">
                    Duration: {scan.duration_seconds}s
                  </div>
                )}
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
