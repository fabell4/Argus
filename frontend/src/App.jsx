import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState('loading')
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadData() {
      try {
        const [healthResponse, summaryResponse] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/power/summary'),
        ])

        if (!healthResponse.ok || !summaryResponse.ok) {
          throw new Error('API request failed')
        }

        const healthData = await healthResponse.json()
        const summaryData = await summaryResponse.json()

        setHealth(healthData.status)
        setSummary(summaryData)
      } catch {
        setError('Unable to reach backend API')
      }
    }

    loadData()
  }, [])

  return (
    <main className="app">
      <h1>Argus</h1>
      <p>Power use reporting dashboard</p>

      <section className="card">
        <h2>Backend health</h2>
        <p>Status: {health}</p>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h2>Power summary</h2>
        {summary ? (
          <ul>
            <li>Daily: {summary.daily_kwh} kWh</li>
            <li>Weekly: {summary.weekly_kwh} kWh</li>
            <li>Monthly: {summary.monthly_kwh} kWh</li>
          </ul>
        ) : (
          <p>Loading summary...</p>
        )}
      </section>
    </main>
  )
}

export default App
