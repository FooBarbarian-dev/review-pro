import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'

// Dashboard
export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: api.getDashboardStats,
  })
}

// Scans
export const useScans = (params?: Parameters<typeof api.getScans>[0]) => {
  return useQuery({
    queryKey: ['scans', params],
    queryFn: () => api.getScans(params),
  })
}

export const useScan = (id: string) => {
  return useQuery({
    queryKey: ['scans', id],
    queryFn: () => api.getScan(id),
    enabled: !!id,
  })
}

export const useCreateScan = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createScan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export const useTriggerRescan = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.triggerRescan,
    onSuccess: (_, scanId) => {
      queryClient.invalidateQueries({ queryKey: ['scans', scanId] })
      queryClient.invalidateQueries({ queryKey: ['scans'] })
    },
  })
}

export const useTriggerAdjudication = () => {
  return useMutation({
    mutationFn: ({
      scanId,
      provider,
      model,
      pattern,
    }: {
      scanId: string
      provider?: string
      model?: string
      pattern?: string
    }) => api.triggerAdjudication(scanId, provider, model, pattern),
  })
}

export const useTriggerClustering = () => {
  return useMutation({
    mutationFn: ({
      scanId,
      algorithm,
      threshold,
    }: {
      scanId: string
      algorithm?: string
      threshold?: number
    }) => api.triggerClustering(scanId, algorithm, threshold),
  })
}

// Findings
export const useFindings = (params?: Parameters<typeof api.getFindings>[0]) => {
  return useQuery({
    queryKey: ['findings', params],
    queryFn: () => api.getFindings(params),
  })
}

export const useFinding = (id: string) => {
  return useQuery({
    queryKey: ['findings', id],
    queryFn: () => api.getFinding(id),
    enabled: !!id,
  })
}

export const useUpdateFindingStatus = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.updateFindingStatus(id, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['findings', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['findings'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

// Clusters
export const useClusters = (params?: Parameters<typeof api.getClusters>[0]) => {
  return useQuery({
    queryKey: ['clusters', params],
    queryFn: () => api.getClusters(params),
  })
}

export const useCluster = (id: string) => {
  return useQuery({
    queryKey: ['clusters', id],
    queryFn: () => api.getCluster(id),
    enabled: !!id,
  })
}

export const useClusterFindings = (clusterId: string) => {
  return useQuery({
    queryKey: ['clusters', clusterId, 'findings'],
    queryFn: () => api.getClusterFindings(clusterId),
    enabled: !!clusterId,
  })
}

// Pattern Comparison
export const usePatternComparison = (scanId: string) => {
  return useQuery({
    queryKey: ['scans', scanId, 'pattern-comparison'],
    queryFn: () => api.getPatternComparison(scanId),
    enabled: !!scanId,
  })
}

export const useRunPatternComparison = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.runPatternComparison,
    onSuccess: (_, scanId) => {
      queryClient.invalidateQueries({
        queryKey: ['scans', scanId, 'pattern-comparison'],
      })
    },
  })
}
