import { RefreshCw } from 'lucide-react'
import { PowerChart } from '@/components/PowerChart'
import { PowerGauge } from '@/components/PowerGauge'
import { EventsTable } from '@/components/EventsTable'
import { useArgus } from '@/hooks/useArgus'

export function Dashboard() {
  const { snapshots, latest, health, isPolling, error, runPoll } = useArgus()

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <div className="page-actions">
          {health && (
            <span className={`status-badge ${health.status === 'ok' ? 'ok' : 'error'}`}>
              {health.status}
            </span>
          )}
          <button
            className="btn-primary"
            onClick={runPoll}
            disabled={isPolling}
          >
            <RefreshCw size={14} className={isPolling ? 'spin' : ''} />
            {isPolling ? 'Polling…' : 'Poll Now'}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="gauges">
        <PowerGauge label="Power" value={latest?.power_watts ?? null} unit="W" metric="power" />
        <PowerGauge label="Load" value={latest?.load_percent ?? null} unit="%" metric="load" />
        <PowerGauge label="Battery" value={latest?.battery_percent ?? null} unit="%" metric="battery" />
        <PowerGauge label="Temperature" value={latest?.temperature_c ?? null} unit="°C" metric="temperature" />
      </section>

      <section className="card">
        <h2 className="section-title">Power History</h2>
        <PowerChart snapshots={snapshots} />
      </section>

      <section className="card">
        <h2 className="section-title">Recent Events</h2>
        <EventsTable />
      </section>

      {health && (
        <footer className="dashboard-footer">
          {health.last_poll_at && (
            <span>Last poll: {new Date(health.last_poll_at).toLocaleString()}</span>
          )}
          {health.next_poll_at && (
            <span>Next poll: {new Date(health.next_poll_at).toLocaleString()}</span>
          )}
        </footer>
      )}
    </div>
  )
}
