const API_URL = 'http://localhost:8000'

// FastAPI reports validation problems as a list of objects under "detail", but
// our own errors are a plain string, so both shapes have to be handled or the
// user sees "[object Object]".
function readErrorMessage(data, status) {
  const detail = data && data.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const field = (first.loc || []).slice(-1)[0]
    return field ? `${field}: ${first.msg}` : first.msg
  }

  return `Request failed (${status})`
}

export async function analyzeLabs(labs) {
  let response

  try {
    response = await fetch(`${API_URL}/analyze_labs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ labs }),
    })
  } catch {
    // fetch only rejects when the request never got there.
    throw new Error('Could not reach the backend. Is it running on port 8000?')
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(readErrorMessage(data, response.status))
  }

  return response.json()
}
