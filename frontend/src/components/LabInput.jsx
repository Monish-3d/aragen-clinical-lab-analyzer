import { useState } from 'react'

const EMPTY_ROW = { test_name: '', value: '', unit: '' }

function LabInput({ onAnalyze, loading }) {
  const [rows, setRows] = useState([{ ...EMPTY_ROW }])

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

  function handleSubmit(event) {
    event.preventDefault()

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
            <button
              type="button"
              className="link-button"
              onClick={() => removeRow(index)}
              disabled={rows.length === 1}
              aria-label={`Remove row ${index + 1}`}
            >
              Remove
            </button>
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
    </form>
  )
}

export default LabInput
