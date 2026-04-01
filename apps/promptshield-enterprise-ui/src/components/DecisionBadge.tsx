import { clsx } from 'clsx'

interface DecisionBadgeProps {
  decision: string
  className?: string
}

const DECISION_STYLES: Record<string, string> = {
  ALLOW: 'bg-green-900/50 text-green-300 border-green-700',
  WARN: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  BLOCK: 'bg-red-900/50 text-red-300 border-red-700',
  REROUTE_WEBSEARCH: 'bg-cyan-900/50 text-cyan-300 border-cyan-700',
  REROUTE_CHEAPER_MODEL: 'bg-blue-900/50 text-blue-300 border-blue-700',
  REQUIRE_CONFIRMATION: 'bg-purple-900/50 text-purple-300 border-purple-700',
}

const DECISION_ICONS: Record<string, string> = {
  ALLOW: '✓',
  WARN: '⚠',
  BLOCK: '✗',
  REROUTE_WEBSEARCH: '↗',
  REROUTE_CHEAPER_MODEL: '↓',
  REQUIRE_CONFIRMATION: '?',
}

export default function DecisionBadge({ decision, className }: DecisionBadgeProps) {
  const styles = DECISION_STYLES[decision] ?? 'bg-slate-700 text-slate-300 border-slate-600'
  const icon = DECISION_ICONS[decision] ?? '•'

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium',
        styles,
        className,
      )}
    >
      <span>{icon}</span>
      <span>{decision}</span>
    </span>
  )
}
