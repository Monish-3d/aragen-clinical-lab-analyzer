import { useState } from 'react'
import LabInput from './components/LabInput'
import ResultsDisplay from './components/ResultsDisplay'
import { analyzeLabs } from './api'
import './App.css'

function App() {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleAnalyze(labs) {
    if (labs.length === 0) {
      setError('Enter at least one test name and value.')
      return
    }

    setLoading(true)
    setError('')

    try {
      setAnalysis(await analyzeLabs(labs))
    } catch (failure) {
      setError(failure.message)
      setAnalysis(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Clinical Lab Results Analyzer</h1>
        <p className="subtitle">
          Classifies lab results as Normal, Warning or Critical against their
          reference ranges, and explains why.
        </p>
      </header>

      <main>
        <LabInput onAnalyze={handleAnalyze} loading={loading} />

        {error && <p className="error">{error}</p>}

        {loading && <p className="loading">Analyzing results...</p>}

        {analysis && !loading && <ResultsDisplay analysis={analysis} />}
      </main>
    </div>
  )
}

export default App
