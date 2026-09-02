# Clinical Lab Results Analyzer

A full-stack app that takes laboratory test results, classifies each one as
Normal, Warning or Critical against its reference range, and uses an LLM to
explain what the result can mean and what to do next.

Built for the GenAI + Full-Stack assignment.

## Problem

Laboratories produce a lot of results, and the interesting part is usually a
small number of abnormal ones. Reading a wall of numbers to find them is slow,
and a bare "abnormal" label does not tell anyone *why* a value was flagged or
what to do about it.

This app sorts results so the ones that need attention come first, and shows
for every result: the value, the reference range it was compared against, the
severity, the reason it was flagged, an explanation of what it can indicate,
and a suggested next step.

## Features

- Enter results in a form, or upload a CSV
- Deterministic classification against the dataset's reference ranges
- Handles numeric tests (Hemoglobin, Ferritin) and categorical ones
  (urine strips reported as Negative, 1+, 2+)
- Results sorted critical first, with counts per severity
- AI-written explanation and next step for every result
- Colour-coded severity, with an icon and a word as well as colour
- A bar on each numeric result showing where the value falls against its range
- Errors reported rather than crashed: unknown tests, missing values, wrong
  units, malformed CSVs
- Classification still works if the LLM is unavailable

## Tech stack

| Part | Choice |
|---|---|
| Backend | Python, FastAPI |
| Tool server | MCP (`mcp` Python SDK, stdio transport) |
| LLM | Google Gemini (`google-genai`), free tier |
| Frontend | React (Vite) |
| Data | Kaggle "Laboratory Test Results – Anonymized Dataset" |

## Architecture

```
React UI
   |
   v
FastAPI  POST /analyze_labs
   |
   v
Agent
   |-- reference lookup ---> MCP server (reference_range_lookup)
   |-- classify              deterministic, no LLM
   |-- route                 critical first
   |-- explain ------------> Gemini
   v
Structured JSON response
   |
   v
React UI
```

The idea to take away: **classification is done by application logic comparing
the value to its reference range. The LLM is only used to explain the result
that logic already produced.** The same input always gets the same severity,
and the model cannot turn a normal result into a critical one.

### Files

```
backend/
  main.py             FastAPI app, /health and POST /analyze_labs
  agent.py            classify -> route -> explain
  classifier.py       severity rules and routing
  reference_data.py   loads the dataset, looks up reference ranges
  mcp_server.py       MCP server exposing reference_range_lookup
  mcp_client.py       talks to that server over stdio
  llm.py              Gemini call, structured output, fallback
  models.py           Pydantic request/response models
  data/               the Kaggle CSV
frontend/src/
  App.jsx             page state
  api.js              calls the backend
  csv.js              CSV reading and validation
  components/         LabInput, ResultsDisplay, SeverityBadge,
                      RangeIndicator
test_data/            three synthetic CSVs
```

## Agent flow

1. Validate the request with Pydantic.
2. Resolve each test's reference range **through the MCP server**, unless the
   upload supplied its own.
3. Classify each result against that range.
4. Sort the results: critical, then warning, then normal.
5. Ask the LLM to explain each result, a few calls at a time.
6. Return the sorted results plus counts per severity.

## MCP

The assignment requires an MCP server, so reference lookup is a real MCP tool
rather than a direct function call.

`mcp_server.py` runs an MCP server named `lab-reference` exposing one tool:

```
reference_range_lookup(test_name)
```

For a numeric test it answers:

```json
{
  "found": true,
  "test_name": "Hemoglobin",
  "reference_range": "12-15",
  "unit": "g/dL",
  "is_numeric": true,
  "min_reference": 12.0,
  "max_reference": 15.0
}
```

For a categorical test the numeric limits are left out:

```json
{
  "found": true,
  "test_name": "Protein (Strip)",
  "reference_range": "Negative",
  "unit": "mg/dL",
  "is_numeric": false
}
```

An unknown test gets a structured answer rather than an exception:

```json
{
  "found": false,
  "test_name": "Glucose",
  "error": "No reference data found for test 'Glucose'."
}
```

`mcp_client.py` starts the server as a subprocess and talks to it over stdio.
One session is opened per request and reused for every test in that request,
so the subprocess starts once rather than once per test.

## Classification logic

### Numeric tests

A value inside the range is normal, and **the boundaries count as normal**:

```
min_reference <= value <= max_reference   ->  NORMAL
```

Outside the range, the result is CRITICAL if **either** rule fires, and
WARNING otherwise:

```
deviation / range_width          > 1.0    (more than one full range width out)
deviation / the limit it crossed > 0.5    (more than half the limit itself)
```

Two rules are needed because one alone gets a whole class of tests wrong.
Measuring in range widths works for a narrow range like Hemoglobin (12-15,
width 3), where 8.1 g/dL scores 1.3 and is correctly critical. But Ferritin's
range is 15-150, so its width is 135 — a ferritin would have to fall below
-120 to score above 1.0, meaning **no low ferritin could ever be flagged
critical**. The second rule compares the deviation against the limit that was
actually crossed, which catches those cases:

| Test | Value | Range widths out | Fraction of the limit | Result |
|---|---|---|---|---|
| Hemoglobin | 8.1 | 1.50 | 0.38 | CRITICAL (first rule) |
| Ferritin | 5 | 0.07 | 0.73 | CRITICAL (second rule) |
| Trombosit | 20 | 0.43 | 0.87 | CRITICAL (second rule) |
| Hemoglobin | 11.0 | 0.33 | 0.08 | WARNING |

Both thresholds are constants at the top of `classifier.py`
(`CRITICAL_RANGE_WIDTHS`, `CRITICAL_BOUNDARY_FRACTION`).

**These thresholds are application rules for this assignment, not medical
guidelines.** The dataset provides reference ranges but no clinical critical
limits for any test, so the warning/critical split had to be defined by the
app. See Limitations.

### Categorical tests

Some tests are text, not numbers, so nothing tries to convert them:

```
result matches the expected value   ->  NORMAL     (Negative when Negative is expected)
3+ or 4+                            ->  CRITICAL
anything else abnormal              ->  WARNING    (1+, 2+, Positive)
```

The dataset is Turkish, so both the result and the expected value go through a
small translation before being compared. That is what makes an English
`Negative` match the dataset's `Negatif`.

Low grades are treated as a warning rather than a critical because the dataset
does so itself: its only abnormal row is `Eritrosit (Strip) = 1+`, whose
recommended follow-up is a repeat urine test.

### Showing it on screen

Each numeric result carries a bar marking the reference range and where the
value sits. The scale extends one whole range width past each limit, which is
the same measure the first critical rule uses, so a marker at the edge of the
bar is exactly the point where a warning would become critical. A value further
out than that sits on the edge rather than vanishing off the end.

Two things worth knowing when reading it:

- The green middle third is always the reference range, whatever the test, so
  bars for different tests can be compared at a glance.
- Because the scale is built from the range width, a result that is critical
  under the *second* rule can still look close to the range. Ferritin 4 is an
  example: it sits just left of the green zone but is critical, because 11 is
  more than half of the lower limit of 15. The reason line under the bar says
  which rule applied.

Categorical tests have no numeric limits, so they have no bar.

### When a result cannot be classified

Unknown test, missing value, non-numeric value for a numeric test, or a unit
that does not match the expected one, all produce `UNKNOWN` with a plain
explanation instead of an error. `UNKNOWN` is not a severity, so it is listed
after the real ones.

A mismatched unit is refused rather than guessed, because 8.1 mg/dL means
something completely different from 8.1 g/dL. Matching ignores case and treats
`µg/L` and `ug/L` as the same.

## LLM usage

Google Gemini, through the `google-genai` SDK. One call per result.

The prompt is given the test name, value, unit, reference range, **the
classification**, **the reason the classifier produced**, and **the routine
follow-up the dataset records for that test**, and is told not to change the
classification.

That last one grounds the suggested next step in the data rather than letting
the model invent one. It needs care, because the dataset's follow-up describes
the test in general, not the value being analysed: `Ferritin` is recorded as
"Iron-rich diet", which is right for a normal result and badly wrong for a
critical one. The prompt says so explicitly - use it when the result is normal,
and suggest something matching the severity when it is not. A ferritin of 4
therefore gets "a critical low value requires a clinical evaluation", while a
ferritin of 45 gets "maintain a balanced, iron-rich diet". The reply is requested as JSON matching a Pydantic
schema (`reason`, `explanation`, `next_step`), so the frontend never parses
free text.

If the call fails for any reason — no API key, network error, rate limit that
outlasts the retries, or a reply that does not match the schema — the result
falls back to the deterministic reason plus a note that the AI explanation is
unavailable. **The classification is never lost because of an LLM problem.**

The free tier is rate limited (see Limitations), so calls are made a few at a
time and a rate-limited call is retried before giving up.

## Setup

Requires Python 3.11+ and Node 18+.

### Environment variables

Copy the example file and fill in your key:

```
cp .env.example .env
```

| Variable | Meaning |
|---|---|
| `GEMINI_API_KEY` | Your key from https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | Model name, default `gemini-3.6-flash` |

`.env` is gitignored and must not be committed.

### Run the backend

From `backend/`:

```
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it with http://localhost:8000/health, or browse the generated API docs at
http://localhost:8000/docs.

### Run the frontend

From `frontend/`:

```
npm install
npm run dev
```

Open http://localhost:5173. The frontend expects the backend on port 8000.

### Run the MCP server

The backend starts the MCP server itself when it needs a lookup, so nothing
extra is needed for the app to work.

To run it on its own:

```
cd backend
python mcp_server.py
```

It uses the stdio transport, so it will sit and wait for an MCP client to
connect. That is expected, not a hang.

## API example

Request:

```
POST /analyze_labs
Content-Type: application/json

{
  "labs": [
    { "test_name": "Hemoglobin", "value": 8.1, "unit": "g/dL" },
    { "test_name": "Protein (Strip)", "value": "Negative", "unit": "mg/dL" }
  ]
}
```

Response:

```json
{
  "results": [
    {
      "test_name": "Hemoglobin",
      "value": 8.1,
      "unit": "g/dL",
      "reference_range": "12-15",
      "status": "CRITICAL",
      "reason": "8.1 is below the reference range 12-15 g/dL by 3.9, which is more than the full width of the range (3).",
      "explanation": "Hemoglobin carries oxygen throughout the body, and a markedly low level can indicate severe anemia...",
      "next_step": "Seek prompt medical evaluation to discuss this result."
    },
    {
      "test_name": "Protein (Strip)",
      "value": "Negative",
      "unit": "mg/dL",
      "reference_range": "Negative",
      "status": "NORMAL",
      "reason": "The result is Negative, which is the expected value for this test.",
      "explanation": "...",
      "next_step": "..."
    }
  ],
  "summary": { "critical": 1, "warning": 0, "normal": 1, "unknown": 0 }
}
```

Results come back already sorted, critical first.

`value` may be a number or a string, so both `8.1` and `"Negative"` are valid.
Optional per-lab fields `reference_range`, `min_reference` and `max_reference`
let a caller supply its own range instead of using the MCP lookup.

Invalid requests get a 422 with a readable message rather than a stack trace.

## CSV format

Required columns: `Test_Name` and `Result`.

Optional: `Unit`, `Reference_Range`, `Min_Reference`, `Max_Reference`,
`Recommended_Followup`. Any other columns are ignored, so the Kaggle dataset
file can be uploaded as-is.

```csv
Test_Name,Result,Unit
Hemoglobin,8.1,g/dL
Eritrosit (Strip),1+,-
```

If the file supplies reference information it is used; otherwise the test is
looked up through the MCP server. That means a test the dataset does not know
about can still be classified if the file brings its own range.

Validation:

- an empty file, a file with only a header, or one missing `Test_Name` or
  `Result` is rejected with a message saying which columns were found
- a row with no test name or no result is reported by line number and skipped,
  and the remaining rows are still analysed
- quoted fields containing commas are handled, and a leading byte order mark is
  stripped

## How to test it

Start the backend and the frontend, open http://localhost:5173, and work
through the cases below.

### The three severities

Upload each file from `test_data/` in turn. Every row in a file should come
back with the severity in its name:

| File | Expected |
|---|---|
| `normal_labs.csv` | 5 normal |
| `warning_labs.csv` | 5 warnings |
| `critical_labs.csv` | 5 criticals |

Then upload `backend/data/lab_test_results_public.csv`, the full Kaggle file.
It should come back as 26 normal and 1 warning, the warning being
`Eritrosit (Strip) = 1+` — which is the one row the dataset itself marks
abnormal, so the app's own judgement agrees with the data.

### Mixed severities and ordering

Enter these by hand to see the ordering and the colours together:

| Test name | Value | Unit | Expected |
|---|---|---|---|
| Hemoglobin | 12.9 | g/dL | Normal |
| Ferritin | 5 | ug/L | Critical |
| Eritrosit (Strip) | 1+ | - | Warning |

The critical result should appear first and the normal one last, whatever
order they were typed in.

### Boundaries

`Hemoglobin` at `12` and at `15` are both normal, since the reference range is
12-15 and the limits count as inside it. `11.99` is a warning.

### Errors

None of these should produce a crash or a stack trace:

| Try this | Expected |
|---|---|
| test name `Glucose` | Not classified — no reference range for it |
| `Hemoglobin` with unit `mg/dL` | Not classified — unit does not match g/dL |
| `Hemoglobin` with value `abc` | Not classified — not a number |
| Analyze with the form empty | "Enter at least one test name and value." |
| Upload a file with no `Test_Name` column | Message naming the columns it did find |
| Upload an empty file | "That file is empty." |
| Stop the backend, then Analyze | "Could not reach the backend..." |

### LLM failure

Rename `.env` (or blank out `GEMINI_API_KEY`) and restart the backend, then
analyze anything. The severity, the reference range and the reason should all
still be there; only the explanation is replaced with "AI explanation is
temporarily unavailable". This is the part worth checking, because it shows the
classification does not depend on the LLM.

### MCP

Reference lookup goes through the MCP server on every request. To see it
failing safely, temporarily rename `backend/mcp_server.py` and analyze
something: every result comes back as not classified with a reason, rather than
the request failing.

## Synthetic test data

`test_data/` holds three CSVs of five rows each, for demonstrating all three
severities:

| File | Contents |
|---|---|
| `normal_labs.csv` | values inside their ranges, including Lökosit at exactly its lower limit |
| `warning_labs.csv` | values moderately outside, plus `Eritrosit (Strip) = 1+` |
| `critical_labs.csv` | values far outside, plus `Eritrosit (Strip) = 3+` |

The values were chosen by running them through the classifier rather than by
eye. `critical_labs.csv` deliberately covers both severity rules: Hemoglobin
and Lökosit trip the range-width rule, while Ferritin and Trombosit trip only
the boundary rule.

None of the three files include reference columns, so uploading them exercises
the MCP lookup.

## Limitations

1. The dataset provides reference ranges but **no clinical critical thresholds
   for any test**, so the split between warning and critical is defined by this
   application, not taken from a medical source.
2. Those thresholds are simple heuristics chosen for this assignment. They are
   not medical guidelines and have not been clinically reviewed.
3. Reference ranges differ between laboratories, methods, and patient groups
   such as age and sex. The single range in the dataset is treated as correct.
4. A single laboratory result is not enough for a diagnosis. Interpretation
   depends on symptoms, history and other results, none of which this app has.
5. LLM explanations can be wrong or incomplete, even when the classification is
   correct.
6. The dataset contains only 27 tests, so anything outside it comes back as not
   classified unless the uploaded file supplies its own reference range.
7. The Gemini free tier allows about 5 requests per minute and 20 per day per
   model. Since every result is explained with its own call, a large file will
   exhaust it and those results will show the fallback message. Each model has
   its own daily allowance, so changing `GEMINI_MODEL` gives a fresh one.

   Models tried while building this, timing a single explanation:

   | Model | Result |
   |---|---|
   | `gemini-3.1-flash-lite` | works, ~1.6s |
   | `gemini-3-flash-preview` | works, ~1.6s |
   | `gemini-3.6-flash` | works, ~2.5s |
   | `gemini-3.5-flash` | works, ~3.0s |
   | `gemini-3.7-flash` | times out (504) |
   | `gemini-flash-latest` | times out (504) |
   | `gemini-2.5-flash`, `gemini-2.5-flash-lite` | 404, retired for new users |

   Note that a retired model still appears in `client.models.list()`, so the
   only way to know a model works is to call it. If every explanation says
   "temporarily unavailable", check the daily quota and the model name before
   assuming the code is broken — the server log prints the real error.
8. This is a hackathon demonstration, not a clinical product.

## Medical disclaimer

This tool provides AI-assisted interpretation based on supplied laboratory
reference ranges. It is not a medical diagnosis. Clinical decisions should be
made by a qualified healthcare professional.
