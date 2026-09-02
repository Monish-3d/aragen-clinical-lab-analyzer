// Test_Name and Result are the two columns we cannot work without. Unit and
// the reference columns are used when they are there.
const REQUIRED_COLUMNS = ['Test_Name', 'Result']

// Small CSV reader written by hand rather than pulling in a library. It has to
// respect quotes: the dataset contains a comment field with a comma inside
// quotes, and Min_Reference / Max_Reference come after it, so splitting on
// every comma would shift those columns onto the wrong values.
export function parseCsv(text) {
  // The Kaggle file starts with a BOM. Left in place it sticks to the first
  // column name, so "Test_Name" would never match the header.
  if (text.charCodeAt(0) === 0xfeff) {
    text = text.slice(1)
  }

  const rows = []
  let row = []
  let field = ''
  let inQuotes = false

  for (let index = 0; index < text.length; index++) {
    const character = text[index]

    if (inQuotes) {
      if (character !== '"') {
        field += character
      } else if (text[index + 1] === '"') {
        field += '"' // a doubled quote inside a quoted field
        index++
      } else {
        inQuotes = false
      }
      continue
    }

    if (character === '"') {
      inQuotes = true
    } else if (character === ',') {
      row.push(field)
      field = ''
    } else if (character === '\n') {
      row.push(field)
      rows.push(row)
      row = []
      field = ''
    } else if (character !== '\r') {
      field += character
    }
  }

  // Whatever is left when the file does not end with a newline.
  if (field !== '' || row.length > 0) {
    row.push(field)
    rows.push(row)
  }

  // Drop blank lines, which are common at the end of a file.
  return rows.filter((cells) => cells.some((cell) => cell.trim() !== ''))
}

function toNumber(text) {
  if (!text || text.trim() === '') {
    return null
  }
  const value = Number(text)
  return Number.isNaN(value) ? null : value
}

export function readLabCsv(text) {
  const rows = parseCsv(text)

  if (rows.length === 0) {
    throw new Error('That file is empty.')
  }

  const header = rows[0].map((name) => name.trim())
  const missing = REQUIRED_COLUMNS.filter((name) => !header.includes(name))

  if (missing.length > 0) {
    throw new Error(
      `Missing required column: ${missing.join(' and ')}. ` +
        `The file has: ${header.join(', ')}`
    )
  }

  const labs = []
  const problems = []

  rows.slice(1).forEach((cells, index) => {
    // +2 because row 0 is the header and people count lines from 1.
    const lineNumber = index + 2

    const row = {}
    header.forEach((name, position) => {
      row[name] = (cells[position] || '').trim()
    })

    // A bad row is reported and skipped rather than failing the whole file.
    if (!row.Test_Name) {
      problems.push(`Line ${lineNumber}: no test name, skipped.`)
      return
    }

    if (!row.Result) {
      problems.push(`Line ${lineNumber}: no result for ${row.Test_Name}, skipped.`)
      return
    }

    labs.push({
      test_name: row.Test_Name,
      value: row.Result,
      unit: row.Unit || null,
      reference_range: row.Reference_Range || null,
      min_reference: toNumber(row.Min_Reference),
      max_reference: toNumber(row.Max_Reference),
      recommended_followup: row.Recommended_Followup || null,
    })
  })

  if (labs.length === 0) {
    throw new Error('No usable rows in that file.')
  }

  return { labs, problems }
}
