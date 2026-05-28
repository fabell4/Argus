import { useState } from 'react'
import { KeyRound, ShieldCheck } from 'lucide-react'
import { useArgus } from '@/hooks/useArgus'

export function ApiKeySetup() {
  const { saveApiKey } = useArgus()
  const [key, setKey] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (key.trim()) saveApiKey(key.trim())
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20">
            <ShieldCheck className="w-7 h-7 text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">API Key Required</h1>
            <p className="mt-1 text-sm text-slate-400">
              Enter your Argus API key to continue. It will be stored in this browser only.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-amber-400" />
              API Key
            </span>
            <input
              type="password"
              value={key}
              autoFocus
              placeholder="Paste your API key here"
              onChange={(e) => setKey(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </label>
          <button
            type="submit"
            disabled={!key.trim()}
            className="w-full px-4 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 rounded-lg text-sm font-semibold transition-colors"
          >
            Connect
          </button>
        </form>

        <p className="text-center text-xs text-slate-600">
          Set <code className="text-slate-500">API_KEY</code> in your Argus{' '}
          <code className="text-slate-500">.env</code> to require authentication.
          Leave it empty to disable auth entirely.
        </p>
      </div>
    </div>
  )
}
