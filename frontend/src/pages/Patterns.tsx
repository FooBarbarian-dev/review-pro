import React, { useState } from 'react'
import { useScans, usePatternComparison, useRunPatternComparison } from '../hooks/useApi'
import { Card, Loading, EmptyState, Button } from '../components/ui'
import { BarChart3, TrendingUp } from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts'

export const Patterns: React.FC = () => {
  const [selectedScanId, setSelectedScanId] = useState<string>('')
  const { data: scansData } = useScans({ status: 'completed', limit: 50 })
  const { data: comparison, isLoading } = usePatternComparison(selectedScanId)
  const runComparisonMutation = useRunPatternComparison()

  const scans = scansData?.results || []

  const handleRunComparison = () => {
    if (selectedScanId) {
      runComparisonMutation.mutate(selectedScanId)
    }
  }

  if (!selectedScanId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Agent Pattern Comparison
          </h1>
          <p className="mt-2 text-gray-600">
            Compare performance of different LLM agent patterns
          </p>
        </div>

        <Card>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select a scan to compare patterns:
              </label>
              <select
                value={selectedScanId}
                onChange={(e) => setSelectedScanId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Choose a scan...</option>
                {scans.map((scan) => (
                  <option key={scan.id} value={scan.id}>
                    {scan.repository.full_name} - {scan.branch} (
                    {scan.commit_sha.slice(0, 7)}) - {scan.total_findings}{' '}
                    findings
                  </option>
                ))}
              </select>
            </div>
            <p className="text-sm text-gray-600">
              This will run all three agent patterns (Post-Processing, Interactive,
              Multi-Agent) on the selected scan's findings and compare their
              performance.
            </p>
          </div>
        </Card>

        <EmptyState
          title="No scan selected"
          description="Select a completed scan to compare agent patterns."
          icon={<BarChart3 className="w-16 h-16" />}
        />
      </div>
    )
  }

  if (isLoading) {
    return <Loading size="lg" text="Loading pattern comparison..." />
  }

  if (!comparison || comparison.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Agent Pattern Comparison
          </h1>
          <p className="mt-2 text-gray-600">
            Compare performance of different LLM agent patterns
          </p>
        </div>

        <Card>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Selected scan:
              </label>
              <select
                value={selectedScanId}
                onChange={(e) => setSelectedScanId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              >
                {scans.map((scan) => (
                  <option key={scan.id} value={scan.id}>
                    {scan.repository.full_name} - {scan.branch} (
                    {scan.commit_sha.slice(0, 7)})
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="primary"
              onClick={handleRunComparison}
              loading={runComparisonMutation.isPending}
            >
              <TrendingUp className="w-4 h-4" />
              Run Pattern Comparison
            </Button>
          </div>
        </Card>

        <EmptyState
          title="No comparison data available"
          description="Run a pattern comparison on this scan to see results."
          icon={<BarChart3 className="w-16 h-16" />}
          action={
            <Button
              variant="primary"
              onClick={handleRunComparison}
              loading={runComparisonMutation.isPending}
            >
              <TrendingUp className="w-4 h-4" />
              Run Pattern Comparison
            </Button>
          }
        />
      </div>
    )
  }

  // Prepare chart data
  const accuracyData = comparison.map((pattern) => ({
    name: pattern.pattern_name.replace(/_/g, ' '),
    'True Positives': pattern.true_positives,
    'False Positives': pattern.false_positives,
    Uncertain: pattern.uncertain,
  }))

  const costData = comparison.map((pattern) => ({
    name: pattern.pattern_name.replace(/_/g, ' '),
    'Total Cost': pattern.total_cost_usd,
    'Avg Cost': pattern.avg_cost_per_finding,
  }))

  const performanceData = comparison.map((pattern) => ({
    name: pattern.pattern_name.replace(/_/g, ' '),
    'Avg Time (ms)': pattern.avg_time_per_finding_ms,
    'FP Reduction': pattern.false_positive_reduction_rate * 100,
  }))

  // Radar chart data for overall comparison
  const radarData = [
    {
      metric: 'Accuracy',
      'Post Processing':
        comparison.find((p) => p.pattern_name === 'post_processing')
          ?.true_positives || 0,
      Interactive:
        comparison.find((p) => p.pattern_name === 'interactive')?.true_positives ||
        0,
      'Multi Agent':
        comparison.find((p) => p.pattern_name === 'multi_agent')?.true_positives ||
        0,
    },
    {
      metric: 'FP Reduction',
      'Post Processing':
        (comparison.find((p) => p.pattern_name === 'post_processing')
          ?.false_positive_reduction_rate || 0) * 100,
      Interactive:
        (comparison.find((p) => p.pattern_name === 'interactive')
          ?.false_positive_reduction_rate || 0) * 100,
      'Multi Agent':
        (comparison.find((p) => p.pattern_name === 'multi_agent')
          ?.false_positive_reduction_rate || 0) * 100,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Agent Pattern Comparison
          </h1>
          <p className="mt-2 text-gray-600">
            Performance comparison across different LLM agent patterns
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={handleRunComparison}
          loading={runComparisonMutation.isPending}
        >
          <TrendingUp className="w-4 h-4" />
          Re-run Comparison
        </Button>
      </div>

      {/* Scan Selector */}
      <Card>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">
            Selected scan:
          </label>
          <select
            value={selectedScanId}
            onChange={(e) => setSelectedScanId(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            {scans.map((scan) => (
              <option key={scan.id} value={scan.id}>
                {scan.repository.full_name} - {scan.branch} (
                {scan.commit_sha.slice(0, 7)})
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Summary Table */}
      <Card title="Pattern Performance Summary">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pattern
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Findings
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  True Positives
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  False Positives
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  FP Reduction
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Cost
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Cost/Finding
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {comparison.map((pattern) => (
                <tr key={pattern.pattern_name}>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {pattern.pattern_name.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {pattern.total_findings}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-green-600 font-medium">
                    {pattern.true_positives}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-red-600 font-medium">
                    {pattern.false_positives}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {(pattern.false_positive_reduction_rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    ${pattern.total_cost_usd.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    ${pattern.avg_cost_per_finding.toFixed(6)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {pattern.avg_time_per_finding_ms.toFixed(0)}ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Accuracy Comparison */}
        <Card title="Verdict Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={accuracyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="True Positives" fill="#10b981" />
              <Bar dataKey="False Positives" fill="#ef4444" />
              <Bar dataKey="Uncertain" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Cost Comparison */}
        <Card title="Cost Analysis">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={costData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Total Cost" fill="#3b82f6" />
              <Bar dataKey="Avg Cost" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Performance Metrics */}
        <Card title="Performance Metrics">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="Avg Time (ms)"
                stroke="#3b82f6"
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="FP Reduction"
                stroke="#10b981"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Overall Comparison Radar */}
        <Card title="Overall Comparison">
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis />
              <Radar
                name="Post Processing"
                dataKey="Post Processing"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.6}
              />
              <Radar
                name="Interactive"
                dataKey="Interactive"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.6}
              />
              <Radar
                name="Multi Agent"
                dataKey="Multi Agent"
                stroke="#f59e0b"
                fill="#f59e0b"
                fillOpacity={0.6}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Insights */}
      <Card title="Key Insights">
        <div className="space-y-3 text-sm">
          <div className="p-3 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-1">
              Post-Processing Filter
            </h4>
            <p className="text-blue-700">
              Fast and cost-effective, ideal for quick triage. Best for large-scale
              scans where speed matters.
            </p>
          </div>
          <div className="p-3 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-900 mb-1">
              Interactive Retrieval
            </h4>
            <p className="text-green-700">
              Balanced approach with context-aware analysis. Good for moderate
              accuracy needs with reasonable cost.
            </p>
          </div>
          <div className="p-3 bg-amber-50 rounded-lg">
            <h4 className="font-medium text-amber-900 mb-1">
              Multi-Agent Collaboration
            </h4>
            <p className="text-amber-700">
              Highest accuracy with detailed analysis and fix recommendations.
              Best for critical findings requiring thorough review.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
