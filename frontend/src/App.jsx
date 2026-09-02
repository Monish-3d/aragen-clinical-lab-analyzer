import { useEffect, useState } from 'react'
import './App.css'

// Placeholder screen for now. It only pings the backend so I can confirm both
// servers are running and talking to each other. The lab input form and the
// results view are built in later steps.
function App() {
  const [backendStatus, setBackendStatus] = useState('checking...')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((response) => response.json())
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus('not reachable'))
  }, [])

  return (
    <div className="app">
      <header>
        <h1>Clinical Lab Results Analyzer</h1>
        <p className="subtitle">
          Classifies lab results as Normal, Warning or Critical and explains why.
        </p>
      </header>

      <main>
        <p className="status">Backend: {backendStatus}</p>
      </main>
    </div>
  )
}

export default App
