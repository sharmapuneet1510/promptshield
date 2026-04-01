import { useState } from 'react'
import { CheckCircle, XCircle } from 'lucide-react'
import axios from 'axios'

export default function Settings() {
  const [apiUrl, setApiUrl] = useState(
    import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  )
  const [apiKey, setApiKey] = useState(import.meta.env.VITE_API_KEY || '')
  const [adminKey, setAdminKey] = useState(import.meta.env.VITE_ADMIN_KEY || '')
  const [testResult, setTestResult] = useState<'idle' | 'ok' | 'error'>('idle')
  const [testMessage, setTestMessage] = useState('')

  const handleTestConnection = async () => {
    setTestResult('idle')
    setTestMessage('')
    try {
      const response = await axios.get(`${apiUrl.replace(/\/api$/, '')}/health`, {
        headers: { 'X-API-Key': apiKey },
        timeout: 5000,
      })
      if (response.data.status === 'ok') {
        setTestResult('ok')
        setTestMessage('Connection successful!')
      } else {
        setTestResult('error')
        setTestMessage(`Unexpected response: ${JSON.stringify(response.data)}`)
      }
    } catch (err: unknown) {
      setTestResult('error')
      const message = err instanceof Error ? err.message : 'Connection failed'
      setTestMessage(message)
    }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure API connection and authentication
        </p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">API Configuration</h2>

        <div>
          <label className="block text-xs text-slate-400 mb-1">API Base URL</label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            placeholder="http://localhost:8000/api"
          />
          <p className="text-xs text-slate-500 mt-1">
            Note: Changing this requires a page reload to take effect.
          </p>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            placeholder="ps-..."
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Admin API Key</label>
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            placeholder="ps-admin-..."
          />
          <p className="text-xs text-slate-500 mt-1">
            Required for analytics, policies, and admin endpoints.
          </p>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleTestConnection}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Test Connection
          </button>
          {testResult !== 'idle' && (
            <div className="flex items-center gap-1.5">
              {testResult === 'ok' ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span
                className={`text-sm ${
                  testResult === 'ok' ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {testMessage}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Environment Info</h2>
        <div className="text-xs text-slate-400 space-y-1.5 font-mono">
          <div>
            <span className="text-slate-500">VITE_API_BASE_URL: </span>
            <span className="text-slate-300">
              {import.meta.env.VITE_API_BASE_URL || '(not set)'}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Mode: </span>
            <span className="text-slate-300">{import.meta.env.MODE}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
