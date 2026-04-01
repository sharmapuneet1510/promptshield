import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  DollarSign,
  Zap,
} from 'lucide-react'
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { fetchSummary } from '../api/analytics'
import StatCard from '../components/StatCard'
import DecisionBadge from '../components/DecisionBadge'

const DECISION_COLORS: Record<string, string> = {
  ALLOW: '#22c55e',
  WARN: '#eab308',
  BLOCK: '#ef4444',
  REROUTE_WEBSEARCH: '#06b6d4',
  REROUTE_CHEAPER_MODEL: '#3b82f6',
  REQUIRE_CONFIRMATION: '#a855f7',
}

export default function Dashboard() {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: fetchSummary,
    refetchInterval: 30_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-slate-400">Loading...</div>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-xl p-4">
        <p className="text-red-400 text-sm">
          Failed to load analytics. Check your API connection in Settings.
        </p>
      </div>
    )
  }

  const pieData = Object.entries(summary.decision_counts).map(([name, value]) => ({
    name,
    value,
  }))

  const blockRate = (summary.block_rate * 100).toFixed(1)
  const totalCost = summary.total_cost_usd.toFixed(4)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">
          Real-time prompt governance overview
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Requests"
          value={summary.total_requests.toLocaleString()}
          icon={<Activity />}
        />
        <StatCard
          label="Total Tokens"
          value={summary.total_tokens.toLocaleString()}
          icon={<Zap />}
        />
        <StatCard
          label="Total Cost"
          value={`$${totalCost}`}
          icon={<DollarSign />}
        />
        <StatCard
          label="Block Rate"
          value={`${blockRate}%`}
          icon={<AlertTriangle />}
          valueClassName={parseFloat(blockRate) > 20 ? 'text-red-400' : 'text-white'}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decision distribution pie chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Decision Distribution
          </h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {pieData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={DECISION_COLORS[entry.name] ?? '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#f1f5f9',
                  }}
                />
                <Legend
                  formatter={(value) => (
                    <span className="text-slate-300 text-xs">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 text-sm text-center py-10">No data yet</p>
          )}
        </div>

        {/* Decision counts table */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Decision Counts
          </h2>
          <div className="space-y-3">
            {Object.entries(summary.decision_counts).map(([decision, count]) => {
              const pct =
                summary.total_requests > 0
                  ? ((count / summary.total_requests) * 100).toFixed(1)
                  : '0'
              return (
                <div key={decision} className="flex items-center justify-between">
                  <DecisionBadge decision={decision} />
                  <div className="flex items-center gap-3">
                    <div className="w-24 bg-slate-700 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: DECISION_COLORS[decision] ?? '#64748b',
                        }}
                      />
                    </div>
                    <span className="text-slate-300 text-sm tabular-nums w-12 text-right">
                      {count.toLocaleString()}
                    </span>
                  </div>
                </div>
              )
            })}
            {Object.keys(summary.decision_counts).length === 0 && (
              <p className="text-slate-500 text-sm">No requests processed yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
