import axios from 'axios'
import type {
  Scan,
  Finding,
  FindingCluster,
  DashboardStats,
  PatternComparison,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Dashboard
export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await api.get('/dashboard/stats/')
  return response.data
}

// Scans
export const getScans = async (params?: {
  status?: string
  repository_id?: string
  limit?: number
  offset?: number
}): Promise<{ results: Scan[]; count: number }> => {
  const response = await api.get('/scans/', { params })
  return response.data
}

export const getScan = async (id: string): Promise<Scan> => {
  const response = await api.get(`/scans/${id}/`)
  return response.data
}

export const createScan = async (data: {
  repository_id: string
  branch?: string
  commit_sha?: string
}): Promise<Scan> => {
  const response = await api.post('/scans/', data)
  return response.data
}

export const triggerRescan = async (scanId: string): Promise<Scan> => {
  const response = await api.post(`/scans/${scanId}/rescan/`)
  return response.data
}

export const triggerAdjudication = async (
  scanId: string,
  provider: string = 'openai',
  model: string = 'gpt-4o',
  pattern: string = 'post_processing'
): Promise<{ task_id: string }> => {
  const response = await api.post(`/scans/${scanId}/adjudicate/`, {
    provider,
    model,
    pattern,
  })
  return response.data
}

export const triggerClustering = async (
  scanId: string,
  algorithm: string = 'dbscan',
  threshold: number = 0.85
): Promise<{ task_id: string }> => {
  const response = await api.post(`/scans/${scanId}/cluster/`, {
    algorithm,
    threshold,
  })
  return response.data
}

// Findings
export const getFindings = async (params?: {
  scan_id?: string
  severity?: string
  status?: string
  tool_name?: string
  file_path?: string
  limit?: number
  offset?: number
}): Promise<{ results: Finding[]; count: number }> => {
  const response = await api.get('/findings/', { params })
  return response.data
}

export const getFinding = async (id: string): Promise<Finding> => {
  const response = await api.get(`/findings/${id}/`)
  return response.data
}

export const updateFindingStatus = async (
  id: string,
  status: string
): Promise<Finding> => {
  const response = await api.patch(`/findings/${id}/`, { status })
  return response.data
}

// Clusters
export const getClusters = async (params?: {
  scan_id?: string
  min_size?: number
  limit?: number
  offset?: number
}): Promise<{ results: FindingCluster[]; count: number }> => {
  const response = await api.get('/clusters/', { params })
  return response.data
}

export const getCluster = async (id: string): Promise<FindingCluster> => {
  const response = await api.get(`/clusters/${id}/`)
  return response.data
}

export const getClusterFindings = async (
  clusterId: string
): Promise<Finding[]> => {
  const response = await api.get(`/clusters/${clusterId}/findings/`)
  return response.data
}

// Pattern Comparison
export const getPatternComparison = async (
  scanId: string
): Promise<PatternComparison[]> => {
  const response = await api.get(`/scans/${scanId}/pattern-comparison/`)
  return response.data
}

export const runPatternComparison = async (
  scanId: string
): Promise<{ task_id: string }> => {
  const response = await api.post(`/scans/${scanId}/compare-patterns/`)
  return response.data
}

export default api
