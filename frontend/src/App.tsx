import { useEffect, useMemo } from 'react'

import './App.css'
import { EventFeed } from './game/feed/EventFeed'
import { getApiBaseUrl, getWsUrl, WsClient } from './net/ws'
import { useGameStore } from './state/store'

function App() {
  const connection = useGameStore((state) => state.connection)
  const snapshot = useGameStore((state) => state.snapshot)
  const events = useGameStore((state) => state.events)
  const setStatus = useGameStore((state) => state.setStatus)
  const setSnapshot = useGameStore((state) => state.setSnapshot)
  const pushEvent = useGameStore((state) => state.pushEvent)
  const setRun = useGameStore((state) => state.setRun)

  const apiBase = useMemo(() => getApiBaseUrl(), [])

  useEffect(() => {
    const client = new WsClient(getWsUrl(), {
      onHello: (payload) => setRun(payload.run_id, undefined),
      onSnapshot: (payload) => setSnapshot(payload),
      onEvent: (payload) => pushEvent(payload),
      onError: (payload) => setStatus('disconnected', payload.message),
      onStatusChange: (status, error) => setStatus(status, error),
    })
    client.connect()
    return () => client.close()
  }, [pushEvent, setRun, setSnapshot, setStatus])

  const handleStart = async () => {
    try {
      await fetch(`${apiBase}/run/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed: Date.now() % 100000 }),
      })
    } catch {
      setStatus('disconnected', 'Failed to start run')
    }
  }

  const handleStop = async () => {
    try {
      await fetch(`${apiBase}/run/stop`, { method: 'POST' })
    } catch {
      setStatus('disconnected', 'Failed to stop run')
    }
  }

  const activePlayer = snapshot?.players.find(
    (player) => player.player_id === snapshot?.active_player_id,
  )

  return (
    <div className="app">
      <header className="top-bar">
        <div className="brand">
          <span className="brand-kicker">Monopoly LLM Benchmark</span>
          <h1>Realtime Mock Arena</h1>
        </div>
        <div className="status">
          <span className={`status-dot ${connection.status}`} />
          <div>
            <div className="status-label">{connection.status}</div>
            {connection.lastError ? <div className="status-error">{connection.lastError}</div> : null}
          </div>
        </div>
        <div className="actions">
          <button className="primary" onClick={handleStart}>
            Start Mock Run
          </button>
          <button className="ghost" onClick={handleStop}>
            Stop Run
          </button>
        </div>
      </header>

      <main className="main-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Game View</h2>
            <span className="panel-subtitle">Snapshot overview</span>
          </div>
          <div className="snapshot-cards">
            <div className="snapshot-card">
              <span className="label">Run</span>
              <span className="value">{snapshot?.run_id ?? 'idle'}</span>
            </div>
            <div className="snapshot-card">
              <span className="label">Turn</span>
              <span className="value">{snapshot?.turn_index ?? '-'}</span>
            </div>
            <div className="snapshot-card">
              <span className="label">Phase</span>
              <span className="value">{snapshot?.phase ?? '-'}</span>
            </div>
            <div className="snapshot-card">
              <span className="label">Active</span>
              <span className="value">{activePlayer?.name ?? '-'}</span>
            </div>
          </div>

          <div className="players">
            <h3>Players</h3>
            <div className="players-table">
              <div className="players-row header">
                <span>Name</span>
                <span>Cash</span>
                <span>Position</span>
                <span>In Jail</span>
              </div>
              {(snapshot?.players ?? []).map((player) => (
                <div className="players-row" key={player.player_id}>
                  <span className="player-name">{player.name}</span>
                  <span className="player-cash">${player.cash}</span>
                  <span>{player.position}</span>
                  <span>{player.in_jail ? 'Yes' : 'No'}</span>
                </div>
              ))}
              {!snapshot && <div className="empty-state">Waiting for snapshot...</div>}
            </div>
          </div>
        </section>

        <aside className="sidebar">
          <EventFeed events={events} snapshot={snapshot} />
        </aside>
      </main>
    </div>
  )
}

export default App
