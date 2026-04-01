import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminClient } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

interface RequestRecord {
  id: string
  request_id: string
  user_id: string
  team_id: string | null
  source: string
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
  decision: string
  classifications: string[]
  misuse_score: number
  route_taken: string | null
  created_at: string
}

const DECISIONS = ['ALL', 'ALLOW', 'WARN', 'BLOCK', 'REROUTE_WEBSEARCH', 'REROUTE_CHEAPER_MODEL', 'REQUIRE_CONFIRMATION']

async function fetchRequests(decision: string): Promise<RequestRecord[]> {
  const params = new URLSearchParams({ limit: '100' })
  if (decision !== 'ALL') params.set('decision', decision)
  const { data } = await adminClient.get<RequestRecord[]>(`/v1/analytics/requests?${params}`)
  return data
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Requests() {
  const [selectedDecision, setSelectedDecision] = useState('ALL')

  const { data = [], isLoading, error } = useQuery({
    queryKey: ['requests', selectedDecision],
    queryFn: () => fetchRequests(selectedDecision),
    refetchInterval: 15_000,
  })

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Requests</h1>
        <p className="text-slate-400 text-sm mt-1">
          Browse and filter precheck request history
        </p>
      </div>

      {/* Decision filter */}
      <div className="flex gap-2 flex-wrap">
        {DECISIONS.map((d) => (
          <button
            key={d}
            onClick={() => setSelectedDecision(d)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              selectedDecision === d
                ? 'bg-indigo-600 border-indigo-500 text-white'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-xl p-4">
          <p className="text-red-400 text-sm">Failed to load requests. Check API connection.</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/80">
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Time</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">User</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Model</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Decision</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Classifications</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Tokens</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Cost</th>
                <th className="text-right px-4 py-3 text-slate-400 font-medium">Misuse</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    Loading...
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-500">
                    No records found.
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                      {formatDate(row.created_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-200 font-mono text-xs max-w-[120px] truncate">
                      {row.user_id}
                    </td>
                    <td className="px-4 py-3 text-slate-300 text-xs max-w-[140px] truncate">
                      {row.model}
                    </td>
                    <td className="px-4 py-3">
                      <DecisionBadge decision={row.decision} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {row.classifications.map((c) => (
                          <span
                            key={c}
                            className="px-1.5 py-0.5 bg-slate-700 text-slate-300 rounded text-xs"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 tabular-nums text-xs">
                      {row.total_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 tabular-nums text-xs">
                      ${row.cost_usd.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={`font-mono text-xs ${
                          row.misuse_score >= 0.7
                            ? 'text-red-400'
                            : row.misuse_score >= 0.4
                            ? 'text-yellow-400'
                            : 'text-green-400'
                        }`}
                      >
                        {row.misuse_score.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {data.length > 0 && (
          <div className="px-4 py-2 border-t border-slate-700 text-xs text-slate-500">
            Showing {data.length} records
          </div>
        )}
      </div>
    </div>
  )
}
