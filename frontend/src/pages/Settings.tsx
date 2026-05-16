import { useEffect, useState } from 'react'
import { useArgus } from '@/hooks/useArgus'
import type { RuntimeConfig } from '@/types'

export function Settings() {
  const { config, updateConfig } = useArgus()
  const [form, setForm] = useState<RuntimeConfig | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) setForm(config)
  }, [config])

  if (!form) return <p className="muted">Loading settings…</p>

  const handleSave = async () => {
    await updateConfig(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
      </div>

      <section className="card settings-card">
        <h2 className="section-title">Scheduler</h2>

        <label className="field">
          <span>Poll interval (minutes)</span>
          <input
            type="number"
            min={1}
            max={10080}
            value={form.poll_interval_minutes}
            onChange={(e) => setForm({ ...form, poll_interval_minutes: Number(e.target.value) })}
          />
        </label>

        <label className="field checkbox-field">
          <input
            type="checkbox"
            checked={form.scheduler_paused}
            onChange={(e) => setForm({ ...form, scheduler_paused: e.target.checked })}
          />
          <span>Pause scheduler</span>
        </label>

        <label className="field checkbox-field">
          <input
            type="checkbox"
            checked={form.scanning_disabled}
            onChange={(e) => setForm({ ...form, scanning_disabled: e.target.checked })}
          />
          <span>Disable scanning</span>
        </label>
      </section>

      <section className="card settings-card">
        <h2 className="section-title">Exporters</h2>
        {(['sqlite', 'prometheus', 'influxdb'] as const).map((exporter) => (
          <label key={exporter} className="field checkbox-field">
            <input
              type="checkbox"
              checked={form.enabled_exporters.includes(exporter)}
              onChange={(e) => {
                const updated = e.target.checked
                  ? [...form.enabled_exporters, exporter]
                  : form.enabled_exporters.filter((ex) => ex !== exporter)
                setForm({ ...form, enabled_exporters: updated })
              }}
            />
            <span>{exporter}</span>
          </label>
        ))}
      </section>

      <div className="settings-actions">
        <button className="btn-primary" onClick={handleSave}>
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}
