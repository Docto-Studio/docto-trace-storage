---
name: Docto Trace — Storage Auditor
description: >
  Audit Google Drive storage on behalf of the user. Use this when the user asks to
  scan their Drive, find zombie files, detect duplicates, analyse storage usage, get
  a cleanup plan, or asks anything related to Google Drive health. This skill runs the
  full audit itself — the user does NOT need to run any CLI command manually.
dependencies: python>=3.10, docto-trace-storage>=0.2.0
---

## Overview

**Docto Trace — Storage Auditor** is an open-source, read-only Google Drive auditing
tool. It recursively traverses a Drive, calculates true folder sizes, detects zombie
files (stale > N months), surfaces duplicate content, and produces a machine-readable
`report.json` (HealthReport schema). All execution is local — no data leaves the user's
machine.

This Skill actively **invokes the CLI** via `scripts/run_scan.py`. You do not need the
user to run the CLI themselves or share a pre-generated report.

---

## When to Invoke This Skill

Trigger this Skill when the user says things like:
- "Scan my Google Drive"
- "Show me what's wasting space in my Drive"
- "Find duplicate files in my Drive"
- "Which files haven't been touched in years?"
- "Give me a Drive cleanup plan"
- "Audit my storage / what's taking up space?"
- "Run docto-trace" or "use the storage auditor"

Also trigger it when the user shares or pastes a `report.json` and asks you to analyse it.

---

## Orchestration Flow

Follow this sequence every time:

### Step 1 — Prerequisites check

Verify `docto-trace-storage` is installed:

```bash
docto-trace --version
```

If the command is not found, install it first:

```bash
pip install docto-trace-storage
```

### Step 2 — Auth check

Check whether a valid token is cached:

```bash
docto-trace login
```

If the user has their own credentials file, use:
```bash
docto-trace login --credentials /path/to/credentials.json
```

For service accounts (non-interactive / CI environments):
```bash
docto-trace login --service-account /path/to/sa-key.json
```

Handle first-run gracefully: the browser will open for OAuth2 consent. Tell the user this
is expected on first run and that the token will be cached for subsequent scans.

### Step 3 — Run the scan

Call `scripts/run_scan.py`, passing the user's intent as flags:

```bash
python scripts/run_scan.py \
  [--root-id FOLDER_ID] \
  [--max-depth N] \
  [--top N] \
  [--stale-threshold MONTHS] \
  [--output DIR] \
  [--credentials PATH] \
  [--service-account PATH]
```

All flags are optional — defaults work for a full "My Drive" scan with sensible thresholds.

The script prints the path to the generated `report.json` as its last line.

### Step 4 — Analyse the report

Call `scripts/analyze_report.py` on the generated `report.json`:

```bash
python scripts/analyze_report.py /path/to/output/report.json
```

This outputs a condensed, structured summary designed to fit within the context window.

### Step 5 — Compose a response

Using the schema in `resources/REPORT_SCHEMA.md` and the interpretation guide in
`resources/ACTION_PLAN_GUIDE.md`, compose a clear, actionable response.

**Standard response format:**

1. **Storage Overview** — total files, total size, max depth (1–2 lines)
2. **Top Largest Folders** — table: rank, name, path, size
3. **Zombie Files** — count, total size, top examples with last-modified date
4. **Duplicate Groups** — count, total wasted bytes, top groups
5. **Action Plan** — ordered by severity (`critical` first), concise bullets

### Step 6 — Follow-up loop

The user can ask follow-up questions without re-scanning. Reason over the already-captured
report and `analyze_report.py` output:

- "Show me only the critical action items"
- "Which zombie files are oldest?"
- "What's the biggest duplicate group?"
- "List zombies last modified before 2021"

Only re-run `run_scan.py` if the user explicitly asks for a fresh scan, or if they change
scan parameters (e.g., different root folder, different stale threshold).

---

## Key Defaults (when user doesn't specify)

| Parameter | Default | Meaning |
|---|---|---|
| Root folder | `root` (My Drive) | Full drive scan |
| Max depth | unlimited | No depth cap |
| Top N folders | 10 | Show 10 largest |
| Stale threshold | 24 months | Zombie cutoff |
| Output dir | `output/` | Where report.json goes |

---

## Read-Only Guarantee

Always remind the user of this if they express concern:
- The tool uses `drive.readonly` and `drive.metadata.readonly` scopes only.
- It **cannot** write, move, rename, or delete any files.
- All data stays on the user's machine — no Docto servers are involved.

---

## Resources

- `resources/REPORT_SCHEMA.md` — Full schema reference for `HealthReport` and all sub-models
- `resources/COMMANDS_REFERENCE.md` — Complete CLI flag documentation
- `resources/ACTION_PLAN_GUIDE.md` — How to interpret and prioritise action_plan items
- `resources/EXAMPLES.md` — Annotated sample report.json excerpts (few-shot guidance)
