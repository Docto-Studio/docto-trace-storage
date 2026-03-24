<h1 align="center">
  🔍 docto-trace-storage
</h1>

<p align="center">
  <strong>Deep storage auditing for Google Drive.</strong><br/>
  Part of the <a href="https://github.com/Docto-Studio">Docto Trace</a> open-source suite.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python" />
  <img src="https://img.shields.io/badge/version-0.2.1-green" />
  <img src="https://img.shields.io/badge/license-Apache_2.0-blue" />
  <img src="https://img.shields.io/badge/access-read--only-red" />
  <img src="https://img.shields.io/badge/data-stays_on_your_machine-brightgreen" />
</p>

---

## What is this?

`docto-trace-storage` is a high-performance, open-source data auditing tool. It is the first module of the **Docto Trace** suite, designed to map and analyze "digital chaos" across cloud storage providers (starting with Google Drive). The goal is to provide deep visibility into storage structures, identifying **digital dementia** (orphaned files, zombies, and duplicates) to prepare organizations for **AI-readiness** and **Centralized Memory** — all safely from your own machine.

> **Read-Only, always.** The tool _never_ modifies or deletes files. It only observes and reports.

> **Your data stays local.** The Drive API is called directly from your machine. No data passes through any Docto infrastructure.

## Installation & Quick Start

The fastest way to get started is using the **onboard** command. It will guide you through creating a virtual environment, installing dependencies, setting up Google Cloud credentials, and running your first scan.

```bash
# 1. Clone the repository
git clone https://github.com/Docto-Studio/docto-trace-storage.git
cd docto-trace-storage

# 2. Run the onboarding wizard
pip install -e .
docto-trace onboard
```

The wizard will handle:
1. **Environment check** (offering to create a `.venv/`)
2. **Dependency installation** (including the optional Interactive UI)
3. **Google Cloud setup** (guiding you through creating your own `credentials.json`)
4. **Authentication** (logging into your Google Drive)
5. **AI-Readiness** (configuring an LLM provider like OpenAI or Anthropic)
6. **Initial Scan** (launching the dashboard immediately)

---

## Features

| Feature | Status |
|---|---|
| Google Drive OAuth2 authentication | ✅ v0.1 |
| Service Account support | ✅ v0.1 |
| Async recursive folder traversal | ✅ v0.1 |
| True cumulative folder sizes | ✅ v0.1 |
| Top-N largest folders (root excluded) | ✅ v0.1 |
| Deep folder detection | ✅ v0.1 |
| `report.json` export (strict Pydantic schema) | ✅ v0.1 |
| Rich terminal summary | ✅ v0.1 |
| 🧟 Digital Dementia detection (stale > N months) | ✅ **v0.2** |
| ♻️ Content deduplication (MD5 + fallback) | ✅ **v0.2** |
| Duplicate file path tracing | ✅ **v0.2** |
| 📊 Modern Streamlit Dashboard UI (`--ui`) | ✅ **v0.2** |
| Actionable remediation `action_plan` | ✅ **v0.2** |
| Bundled credentials (zero-setup for end users) | ✅ **v0.2** |
| Bring Your Own Credentials (`setup` wizard) | ✅ **v0.2** |
| `login` / `logout` auth lifecycle | ✅ **v0.2** |

---

## Claude Skill (AI-native interface)

`docto-trace-storage` ships with a ready-to-use **Claude Skill** that lets you audit your Google Drive through natural language — no terminal required.

```
User → "Scan my Drive and find what's wasting space"
Claude → runs docto-trace scan → analyses report.json → responds with insights
```

The Skill **actively invokes the CLI on your machine** via a thin subprocess wrapper.
It follows the exact same read-only guarantee as the CLI itself.

### Install the Skill

```bash
# 1. Package the skill
cd skill/
zip -r docto-trace-storage.zip docto-trace-storage/

# 2. Upload to Claude → claude.ai/customize/skills
```

**Enterprise admins** can provision the Skill org-wide via `Admin → Customize → Skills`.
See [`skill/README_SKILL.md`](./skill/README_SKILL.md) for the full deployment guide.

### Example prompts

| Prompt | What happens |
|---|---|
| "Scan my Google Drive" | Full audit, default settings |
| "Find duplicate files in my Drive" | Scan + filter to duplicate groups |
| "Which files haven't been touched in 3 years?" | Scan with `--stale-threshold 36` |
| "Show me my 20 largest folders" | Scan with `--top 20` |

> The CLI (`pip install docto-trace-storage`) works fully standalone — the Skill is an additive layer that delegates 100% to it.

---

## Trust & Privacy

**Are you handing your private Drive to a stranger's app?** No.

1. **Read-only scopes only** — the OAuth2 consent grants only `drive.readonly` and `drive.metadata.readonly`. The API physically cannot write, move, or delete anything.
2. **100% local execution** — your credentials, your token, and your Drive data never leave your machine. There is no Docto backend, no telemetry, no analytics.
3. **Bring Your Own Credentials** — you can create your own Google Cloud project and register your own OAuth2 app in ~5 minutes. Your token is then issued against _your_ GCP project, which you control fully.

```bash
# Create your own GCP credentials (interactive wizard)
docto-trace setup
```

See [Using Your Own Google Cloud Credentials](#using-your-own-google-cloud-credentials) for the full guide.

---

## Installation

### For end users (zero setup)

The package ships with Docto's OAuth2 credentials bundled inside. Install from PyPI and scan — the browser consent screen is the only step needed.

```bash
# Install from PyPI
pip install docto-trace-storage

# Scan immediately — no credentials.json needed
docto-trace scan
```

### From source (contributors / developers)

```bash
git clone https://github.com/Docto-Studio/docto-trace-storage.git
cd docto-trace-storage

# Install editable with dev tools
pip install -e ".[dev]"
```

### Build your own wheel

```bash
python -m build --wheel
# → dist/docto_trace_storage-0.2.1-py3-none-any.whl
```

**Requirements:** Python 3.10+

---

## Quick Start

```bash
# Check version
docto-trace --version      # → docto-trace-storage v0.2.1

# Option A — Zero setup (uses bundled Docto credentials)
docto-trace scan            # browser opens for OAuth2 consent on first run

# Option B — Full control (your own GCP project)
docto-trace setup           # guided 4-step wizard
docto-trace login           # authenticate
docto-trace scan            # run audit
docto-trace logout          # clear session
```

---

## CLI Reference

### `docto-trace ui`

Launches a modern, sleek, interactive Streamlit dashboard to visualize the generated `report.json`. Features a beautiful Dark Theme, Top 10 folder grid, precise data storage metrics, and actionable item tables for addressing Digital Dementia.

```bash
docto-trace ui output/report.json
```

### `docto-trace --version` / `-v`

```bash
docto-trace --version   # docto-trace-storage v0.2.1
docto-trace -v          # same
```

### `docto-trace setup`

Interactive 4-step wizard to create your **own** Google Cloud project and OAuth2 credentials. Run this once if you want full control over the app registration.

```bash
docto-trace setup
docto-trace setup --output ~/my-creds.json
```

### `docto-trace login`

Authenticate with Google Drive and cache the token locally. Subsequent commands reuse the cached token silently.

```bash
docto-trace login
docto-trace login --credentials ./my-credentials.json
docto-trace login --service-account ./sa-key.json   # skip browser flow
```

### `docto-trace logout`

Delete the cached token. The next `scan` or `login` will trigger a fresh browser flow.

```bash
docto-trace logout
docto-trace logout --revoke     # also revoke on Google's servers
```

### `docto-trace scan`

The core command. Traverses Google Drive, runs all audits, and produces `report.json`.

```bash
# Full scan with defaults
docto-trace scan

# Scan and automatically launch the interactive UI dashboard
docto-trace scan --ui

# Narrow to a specific folder by Drive ID
docto-trace scan --root-id 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms

# Cap depth, show top 20, custom output dir
docto-trace scan --max-depth 5 --top 20 --output ./reports/

# Zombie threshold: flag files not modified in 12 months (default: 24)
docto-trace scan --stale-threshold 12

# Use your own credentials file
docto-trace scan --credentials ./my-credentials.json

# Use a service account (no browser flow)
docto-trace scan --service-account ./sa-key.json
```

| Flag | Default | Description |
|---|---|---|
| `--root-id` / `-r` | `root` | Drive folder ID to start from |
| `--max-depth` / `-d` | unlimited | Max folder depth to traverse |
| `--top` / `-n` | `10` | Top-N largest folders to show |
| `--deep-threshold` | `5` | Depth to flag as "deep" |
| `--stale-threshold` / `-S` | `24` | Months without modification = zombie |
| `--credentials` / `-c` | `credentials.json` | OAuth2 credentials file |
| `--output` / `-o` | `output/` | Directory for `report.json` |
| `--ui` / `--no-ui` | `--no-ui` | Auto-launch Streamlit dashboard |
| `--service-account` / `-s` | _(none)_ | Service account key path |

---

## Terminal Output Example

```
🔐 Authenticating with Google Drive…
ℹ️  Using Docto bundled credentials. Run docto-trace setup to use your own.
🌐 Opening browser for Google Drive authorization…  ← first run only

🔍 Scanning: My Drive
⠙ Traversing folders… [00:18]

─────────────── 📦 Storage Overview ───────────────
  Root:          My Drive
  Total files:   14,832
  Total folders: 1,204
  Total size:    48.3 GB
  Max depth:     9

─────────────── 🏆 Top 10 Largest Folders ───────────────
 Rank  Folder     Path              Files    Size
 1     Projects   My Drive/Projects 8,241    31.2 GB
 2     Archive    My Drive/Archive  3,102    10.5 GB

─────────────── 🧟 Zombie Files (381 stale) ───────────────
 File             Path                             Last Modified  Size
 old_invoice.pdf  My Drive/Finance/old_invoice.pdf  2020-01-15    2.1 MB

─────────────── ♻️  Duplicate Groups (70 groups · 104 MB wasted) ───────────────
 Fingerprint       Path                                  Size/copy  Wasted
 c8cd4fe0ab7a7fe8… My Drive/Backup/8CDA554B…mov          12.0 MB    12.0 MB
 (2 copies)        My Drive/Photos/8CDA554B…mov

──────────────── ✅ Report saved ────────────────
  Output: output/report.json
```

---

## Report Schema (v0.2.1)

The output `report.json` follows the `HealthReport` Pydantic schema:

```json
{
  "schema_version": "0.2.1",
  "generated_at": "2026-03-23T10:00:00Z",
  "storage_tree": { "root_name": "My Drive", "total_files": 14832, "total_size_bytes": 51876044800 },
  "insights": {
    "top_folders": [...],
    "deep_folders": [...]
  },
  "zombies": [
    { "file_id": "...", "name": "old_invoice.pdf", "path": "My Drive/Finance/old_invoice.pdf",
      "last_modified": "2020-01-15T10:30:00Z", "size_bytes": 2202009, "reason": "stale" }
  ],
  "duplicates": [
    { "fingerprint": "c8cd4fe0…", "files": ["id1", "id2"],
      "file_names": ["invoice_final.pdf", "invoice_copy.pdf"],
      "file_paths": ["My Drive/Docs/invoice_final.pdf", "My Drive/Backup/invoice_copy.pdf"],
      "size_bytes_per_copy": 2097152, "wasted_bytes": 2097152 }
  ],
  "action_plan": [
    { "severity": "warning",  "category": "zombie",    "description": "..." },
    { "severity": "critical", "category": "duplicate", "description": "..." }
  ]
}
```

**Deduplication strategy:**
- **Primary key** — `md5Checksum` from the Drive API (binary files: PDFs, images, Office docs)
- **Fallback key** — `"<size_bytes>:<normalized_name>"` for Google-native files (Docs, Sheets, Slides)

---

## Using Your Own Google Cloud Credentials

If you want full control over the OAuth2 app registration — so your consent screen, quotas, and audit logs belong entirely to you — run the setup wizard:

```bash
docto-trace setup
```

It walks you through 4 steps, opening each Google Cloud Console page in your browser:

1. **Create a GCP project** — gives you ownership of the app
2. **Enable the Google Drive API** — only the two read-only scopes
3. **Configure the OAuth2 consent screen** — add yourself as a test user
4. **Download `credentials.json`** — the wizard validates it locally

Then authenticate with your own credentials:

```bash
docto-trace login --credentials ./credentials.json
docto-trace scan  --credentials ./credentials.json
```

You can revoke access at any time from [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials), independently of the Docto project.

---

## Configuration

All settings can be overridden with environment variables prefixed `DOCTO_TRACE_`, or in a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `DOCTO_TRACE_CREDENTIALS_PATH` | `credentials.json` | OAuth2 credentials file |
| `DOCTO_TRACE_TOKEN_PATH` | `token.json` | Cached token path |
| `DOCTO_TRACE_SERVICE_ACCOUNT_PATH` | _(none)_ | Service account key path |
| `DOCTO_TRACE_MAX_DEPTH` | _(unlimited)_ | Max folder nesting to traverse |
| `DOCTO_TRACE_DEEP_FOLDER_THRESHOLD` | `5` | Depth to flag as "deep" |
| `DOCTO_TRACE_TOP_N` | `10` | Top-N largest folders |
| `DOCTO_TRACE_STALE_THRESHOLD_MONTHS` | `24` | Zombie detection cutoff (months) |
| `DOCTO_TRACE_OUTPUT_DIR` | `output/` | Report output directory |
| `DOCTO_TRACE_PAGE_SIZE` | `1000` | Drive API items per page |

---

## Development

```bash
make install    # Install with dev dependencies
make lint       # Lint with ruff
make fix        # Auto-fix lint issues
make test       # Run unit tests (no credentials needed)
make typecheck  # Run mypy
```

**Tests run entirely offline** — no Google credentials required:

```bash
python -m pytest tests/ -v
# 48 passed in 0.18s
```

---

## Architecture

```
docto_trace/
├── cli.py                  # Typer root entry point
├── config.py               # Pydantic settings (env-var overridable)
├── data/
│   └── credentials.json    # Bundled Docto OAuth2 credentials (package resource)
├── auth/
│   ├── google_drive.py     # OAuth2 + service account flow (bundled fallback)
│   └── token_store.py      # Token serialization
├── connectors/
│   ├── base.py             # AbstractConnector interface
│   └── google_drive.py     # Drive API (async, paginated, thread-safe)
├── engine/
│   ├── traversal.py        # Iterative BFS tree builder (bounded concurrency)
│   ├── analytics.py        # Phase 1: top-N, deep-folder analytics
│   └── auditor.py          # Phase 2: zombie detection + deduplication
├── schemas/
│   ├── storage.py          # FileNode, FolderNode, StorageTree
│   └── report.py           # HealthReport, ZombieFile, DuplicateGroup, …
└── commands/
    ├── setup.py            # `docto-trace setup`  — BYOC wizard
    ├── login.py            # `docto-trace login`  — OAuth2 flow
    ├── logout.py           # `docto-trace logout` — clear token
    ├── scan.py             # `docto-trace scan`   — core audit command
    └── report.py           # `docto-trace report` — extended report (v0.3)
```

**Key design decisions:**

- **Bundled credentials** — `docto_trace/data/credentials.json` is shipped inside the wheel via `importlib.resources`, enabling zero-setup for end users. Technical users override with `--credentials` or `docto-trace setup`.
- **Schema-first** — all data models defined in Pydantic before any logic is written; `report.json` is machine-readable by other Docto modules.
- **Pure audit functions** — `analytics.py` and `auditor.py` are pure functions with no I/O; trivially unit-testable without credentials.
- **Iterative BFS traversal** — avoids Python stack overflows on large Drives; bounded to `MAX_CONCURRENT=20` parallel API calls via `asyncio.Semaphore`.
- **Thread-safe HTTP** — each thread-pool worker gets its own `httplib2.Http` via `threading.local`, preventing socket corruption.

---

## Roadmap

| Version | Focus |
|---|---|
| v0.1 | Structural mapping — folder sizes, deep nesting |
| **v0.2** | **Data hygiene — digital dementia detection, deduplication, Streamlit UI dashboard, auth lifecycle** |
| v0.3 | Extended reporting — owner analysis, sharing audit, cost estimation |
| v0.4 | AI readiness score — structured/unstructured ratio, naming entropy |

---

## License

Apache 2.0 © [Docto Studio](https://github.com/Docto-Studio)
