import { clsx } from 'clsx'
import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: string | number
  icon?: ReactNode
  trend?: {
    value: number
    label?: string
  }
  className?: string
  valueClassName?: string
}

export default function StatCard({
  label,
  value,
  icon,
  trend,
  className,
  valueClassName,
}: StatCardProps) {
  return (
    <div
      className={clsx(
        'bg-slate-800 border border-slate-700 rounded-xl p-5 flex flex-col gap-2',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-sm font-medium">{label}</span>
        {icon && (
          <span className="text-slate-500 w-5 h-5">{icon}</span>
        )}
      </div>
      <div className={clsx('text-2xl font-bold text-white', valueClassName)}>
        {value}
      </div>
      {trend && (
        <div
          className={clsx(
            'text-xs font-medium',
            trend.value >= 0 ? 'text-green-400' : 'text-red-400',
          )}
        >
          {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value).toFixed(1)}%
          {trend.label && <span className="text-slate-500 ml-1">{trend.label}</span>}
        </div>
      )}
    </div>
  )
}
