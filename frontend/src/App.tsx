import { useWebSocket } from './hooks/useWebSocket'
import type { ConnectionStatus } from './hooks/useWebSocket'
import './App.css'

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connecting: { color: '#f59e0b', label: 'Connecting...' },
  connected: { color: '#22c55e', label: 'Connected' },
  reconnecting: { color: '#f59e0b', label: 'Reconnecting...' },
  disconnected: { color: '#ef4444', label: 'Disconnected' },
  error: { color: '#ef4444', label: 'Connection Error' },
  taken_over: { color: '#9ca3af', label: 'Session Taken Over' },
}

function App() {
  const { status, sessionId, lastMessage, retry } = useWebSocket()
  const config = STATUS_CONFIG[status]

  return (
    <div className="app">
      <div className="card">
        <h1>Bambu Dashboard</h1>
        <p className="subtitle">WebSocket Connection Status</p>

        <div className="status-row">
          <span
            className="status-dot"
            style={{ backgroundColor: config.color }}
          />
          <span className="status-label">{config.label}</span>
        </div>

        {sessionId && (
          <p className="session-id">
            Session: <code>{sessionId}</code>
          </p>
        )}

        {status === 'taken_over' && (
          <p className="info-text">Session taken over by another tab</p>
        )}

        {status === 'reconnecting' && (
          <p className="info-text">Attempting to reconnect to server...</p>
        )}

        {status === 'error' && (
          <div className="error-section">
            <p className="info-text">Cannot connect to server</p>
            <button className="retry-btn" onClick={retry}>
              Retry Connection
            </button>
          </div>
        )}

        {status === 'disconnected' && (
          <div className="error-section">
            <p className="info-text">Session expired</p>
            <button className="retry-btn" onClick={retry}>
              New Session
            </button>
          </div>
        )}

        {lastMessage && (
          <div className="last-message">
            <span className="label">Last message:</span>{' '}
            <code>{lastMessage.type as string}</code>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
