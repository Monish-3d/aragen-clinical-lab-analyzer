import { useState } from 'react'
import { readLabCsv } from '../csv'

const EMPTY_ROW = { test_name: '', value: '', unit: '' }

function LabInput({ onAnalyze, loading }) {
  const [rows, setRows] = useState([{ ...EMPTY_ROW }])
  const [csvProblems, setCsvProblems] = useState([])
  const [csvError, setCsvError] = useState('')
  const [csvName, setCsvName] = useState('')

  function updateRow(index, field, value) {
    const updated = rows.map((row, position) =>
      position === index ? { ...row, [field]: value } : row
    )
    setRows(updated)
  }

  function addRow() {
    setRows([...rows, { ...EMPTY_ROW }])
  }

  function removeRow(index) {
    setRows(rows.filter((row, position) => position !== index))
  }

  function handleFile(event) {
    const file = event.target.files[0]
    if (!file) {
      return
    }

    setCsvError('')
    setCsvProblems([])
    setCsvName(file.name)

    const reader = new FileReader()

    reader.onload = () => {
      try {
        // Bad rows are reported but the good ones are still analysed, so one
        // broken line does not waste the whole upload.
        const { labs, problems } = readLabCsv(reader.result)
        setCsvProblems(problems)
        onAnalyze(labs)
      } catch (failure) {
        setCsvError(failure.message)
      }
    }

    reader.onerror = () => setCsvError('Could not read that file.')
    reader.readAsText(file)

    // Clear the input so picking the same file again still fires onChange.
    event.target.value = ''
  }

  function handleSubmit(event) {
    event.preventDefault()
    setCsvError('')
    setCsvProblems([])
    setCsvName('')

    // Drop rows the user left completely blank, then send the rest. The
    // backend still validates - this only avoids an obvious 422 when someone
    // adds a row and does not fill it in.
    const labs = rows
      .filter((row) => row.test_name.trim() !== '' || row.value.trim() !== '')
      .map((row) => ({
        test_name: row.test_name.trim(),
        value: row.value.trim(),
        unit: row.unit.trim() || null,
      }))

    onAnalyze(labs)
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Enter lab results</h2>

      <div className="lab-rows">
        <div className="lab-row lab-row-header">
          <span>Test name</span>
          <span>Value</span>
          <span>Unit</span>
          <span></span>
        </div>

        {rows.map((row, index) => (
          <div className="lab-row" key={index}>
            <input
              value={row.test_name}
              onChange={(event) => updateRow(index, 'test_name', event.target.value)}
              placeholder="Hemoglobin"
              aria-label={`Test name for row ${index + 1}`}
            />
            <input
              value={row.value}
              onChange={(event) => updateRow(index, 'value', event.target.value)}
              placeholder="12.9 or Negative"
              aria-label={`Value for row ${index + 1}`}
            />
            <input
              value={row.unit}
              onChange={(event) => updateRow(index, 'unit', event.target.value)}
              placeholder="g/dL"
              aria-label={`Unit for row ${index + 1}`}
            />
            {/* Nothing to remove when there is only one row, and a greyed
                out button that never does anything is just confusing. */}
            {rows.length > 1 ? (
              <button
                type="button"
                className="link-button"
                onClick={() => removeRow(index)}
                aria-label={`Remove row ${index + 1}`}
              >
                Remove
              </button>
            ) : (
              <span />
            )}
          </div>
        ))}
      </div>

      <div className="form-actions">
        <button type="button" className="secondary" onClick={addRow}>
          Add another test
        </button>
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      <div className="upload">
        <label htmlFor="csv-file">Or upload a CSV</label>
        <input
          id="csv-file"
          type="file"
          accept=".csv,text/csv"
          onChange={handleFile}
          disabled={loading}
        />
        <p className="hint">
          Needs a Test_Name and Result column. Unit, Reference_Range,
          Min_Reference and Max_Reference are used if present.
        </p>

        {csvName && !csvError && <p className="hint">Loaded {csvName}</p>}

        {csvError && <p className="error">{csvError}</p>}

        {csvProblems.length > 0 && (
          <ul className="problems">
            {csvProblems.map((problem, index) => (
              <li key={index}>{problem}</li>
            ))}
          </ul>
        )}
      </div>
    </form>
  )
}

export default LabInput
