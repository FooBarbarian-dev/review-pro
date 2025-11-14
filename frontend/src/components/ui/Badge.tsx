import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'info' | 'default'
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className = '',
}) => {
  const variantClasses = {
    critical: 'badge-critical',
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
    info: 'badge-info',
    default: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`badge ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  )
}

interface SeverityBadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  className?: string
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  className,
}) => {
  return (
    <Badge variant={severity} className={className}>
      {severity.toUpperCase()}
    </Badge>
  )
}

interface StatusBadgeProps {
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'open' | 'fixed' | 'false_positive' | 'accepted_risk' | 'wont_fix'
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className,
}) => {
  const statusColors: Record<string, string> = {
    // Scan statuses
    pending: 'bg-gray-100 text-gray-800',
    queued: 'bg-blue-100 text-blue-800',
    running: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-800',
    // Finding statuses
    open: 'bg-red-100 text-red-800',
    fixed: 'bg-green-100 text-green-800',
    false_positive: 'bg-purple-100 text-purple-800',
    accepted_risk: 'bg-yellow-100 text-yellow-800',
    wont_fix: 'bg-gray-100 text-gray-800',
  }

  const displayText = status.replace(/_/g, ' ').toUpperCase()

  return (
    <span className={`badge ${statusColors[status] || statusColors.pending} ${className}`}>
      {displayText}
    </span>
  )
}
