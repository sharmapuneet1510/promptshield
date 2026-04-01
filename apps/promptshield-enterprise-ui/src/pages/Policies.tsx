import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminClient, apiClient } from '../api/client'
import { Save } from 'lucide-react'

interface PolicyConfig {
  thresholds: {
    max_input_tokens: number
    max_cost_usd: number
    max_daily_requests: number
    max_daily_spend_usd: number
    warn_at_token_pct: number
    warn_at_cost_pct: number
  }
  routing: {
    warn_on_search_like: boolean
    block_oversized: boolean
    reroute_search_to_web: boolean
    cheaper_model_fallback: string | null
    blocked_models: string[]
  }
}

async function fetchPolicies(): Promise<PolicyConfig> {
  const { data } = await apiClient.get<PolicyConfig>('/v1/policies')
  return data
}

async function updatePolicies(update: Partial<PolicyConfig>): Promise<void> {
  await adminClient.put('/v1/policies', update)
}

export default function Policies() {
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)

  const { data: config, isLoading } = useQuery({
    queryKey: ['policies'],
    queryFn: fetchPolicies,
  })

  const [form, setForm] = useState<Partial<PolicyConfig>>({})

  const mutation = useMutation({
    mutationFn: updatePolicies,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  if (isLoading || !config) {
    return <div className="text-slate-400">Loading...</div>
  }

  const thresholds = { ...config.thresholds, ...(form.thresholds ?? {}) }
  const routing = { ...config.routing, ...(form.routing ?? {}) }

  const handleSave = () => {
    mutation.mutate(form)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-white">Policies</h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure token limits, cost thresholds, and routing rules.
        </p>
      </div>

      {/* Thresholds */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">Thresholds</h2>
        <div className="grid grid-cols-2 gap-4">
          {(
            [
              ['max_input_tokens', 'Max Input Tokens', 'number'],
              ['max_cost_usd', 'Max Cost (USD)', 'number'],
              ['max_daily_requests', 'Daily Request Limit', 'number'],
              ['max_daily_spend_usd', 'Daily Spend Limit (USD)', 'number'],
              ['warn_at_token_pct', 'Warn at Token %', 'number'],
              ['warn_at_cost_pct', 'Warn at Cost %', 'number'],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <label className="block text-xs text-slate-400 mb-1">{label}</label>
              <input
                type="number"
                value={thresholds[key]}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    thresholds: {
                      ...thresholds,
                      [key]: parseFloat(e.target.value),
                    },
                  }))
                }
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Routing */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">Routing Rules</h2>
        <div className="space-y-3">
          {(
            [
              ['warn_on_search_like', 'Warn on search-like prompts'],
              ['block_oversized', 'Block oversized prompts'],
              ['reroute_search_to_web', 'Reroute search-like to web'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={routing[key]}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    routing: { ...routing, [key]: e.target.checked },
                  }))
                }
                className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm text-slate-300">{label}</span>
            </label>
          ))}

          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Cheaper Model Fallback
            </label>
            <input
              type="text"
              value={routing.cheaper_model_fallback ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  routing: {
                    ...routing,
                    cheaper_model_fallback: e.target.value || null,
                  },
                }))
              }
              placeholder="e.g. gpt-4o-mini"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={mutation.isPending || Object.keys(form).length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          {mutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
        {saved && <span className="text-green-400 text-sm">Saved successfully.</span>}
        {mutation.isError && (
          <span className="text-red-400 text-sm">Failed to save. Check admin key.</span>
        )}
      </div>
    </div>
  )
}
