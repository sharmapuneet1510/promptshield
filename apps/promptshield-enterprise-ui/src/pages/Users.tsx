import { useQuery } from '@tanstack/react-query'
import { fetchUserStats, type UserStat } from '../api/analytics'
import { Shield } from 'lucide-react'

function MisuseBar({ score }: { score: number }) {
  const color =
    score >= 0.7 ? 'bg-red-500' : score >= 0.4 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-slate-700 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full ${color}`}
          style={{ width: `${Math.min(score * 100, 100)}%` }}
        />
      </div>
      <span
        className={`text-xs font-mono ${
          score >= 0.7
            ? 'text-red-400'
            : score >= 0.4
            ? 'text-yellow-400'
            : 'text-green-400'
        }`}
      >
        {score.toFixed(2)}
      </span>
    </div>
  )
}

export default function Users() {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['analytics', 'users'],
    queryFn: fetchUserStats,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Users</h1>
        <p className="text-slate-400 text-sm mt-1">
          Per-user usage statistics and misuse analysis
        </p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left px-4 py-3 text-slate-400 font-medium">User ID</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Requests</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Tokens</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Cost (USD)</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Misuse Score</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Daily Limit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-500">
                    Loading...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-500">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((user: UserStat) => (
                  <tr
                    key={user.user_id}
                    className="hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Shield className="w-3 h-3 text-slate-500" />
                        <span className="text-slate-200 font-mono text-xs">
                          {user.user_id}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 tabular-nums">
                      {user.request_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 tabular-nums">
                      {user.total_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 tabular-nums">
                      ${user.total_cost_usd.toFixed(4)}
                    </td>
                    <td className="px-4 py-3">
                      <MisuseBar score={user.avg_misuse_score} />
                    </td>
                    <td className="px-4 py-3 text-right text-slate-400 text-xs">
                      {user.daily_request_limit != null
                        ? user.daily_request_limit.toLocaleString()
                        : 'default'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
