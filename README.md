<h1 align="center">
  🔍 docto-trace-storage
</h1>

<p align="center">
  <strong>Deep storage auditing for Google Drive.</strong><br/>
  Part of the <a href="https://github.com/Docto-Studio">Docto Trace</a> open-source suite.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python" />
  <img src="https://img.shields.io/badge/version-0.1.0--alpha-orange" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <img src="https://img.shields.io/badge/read--only-true-red" />
</p>

---

## What is this?

`docto-trace-storage` maps the "digital chaos" inside your Google Drive. It recursively traverses your entire storage, calculates the **true size** of every folder (something the native Drive UI doesn't show), and surfaces structural insights — the largest folders, the most deeply nested paths, and a full JSON report ready for downstream automation.

> **Read-Only by Default.** The tool _never_ deletes or moves files. It only observes and reports.

---

## Features (v0.1 — MVP)

| Feature | Status |
|---|---|
| Google Drive OAuth2 authentication | ✅ |
| Service Account support | ✅ |
| Async recursive folder traversal | ✅ |
| Correct cumulative folder sizes | ✅ |
| Top-N largest folders | ✅ |
| Deep folder detection | ✅ |
| `report.json` export (strict schema) | ✅ |
| Rich terminal summary | ✅ |
| Zombie file detection | 🔜 v0.2 |
| Content deduplication (MD5/SHA256) | 🔜 v0.2 |
| Actionable remediation plan | 🔜 v0.2 |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/Docto-Studio/docto-trace-storage.git
cd docto-trace-storage

# Install (editable, with dev tools)
pip install -e ".[dev]"
```

---

## Authentication Setup

### Option A — OAuth2 (User Account)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services → Credentials**.
2. Create an **OAuth 2.0 Client ID** (Desktop App).
3. Download the JSON and save it as `credentials.json` in the project root.
4. Run any `docto-trace` command — a browser tab will open for consent on first run.
   The token is cached in `token.json` for future runs.

### Option B — Service Account

1. Create a **Service Account** in Google Cloud Console.
2. Grant it access to the Drive folders you want to scan.
3. Download the key JSON and pass it via `--service-account`:

```bash
docto-trace scan --service-account /path/to/key.json
```

---

## Usage

```bash
# Scan your entire My Drive (requires credentials.json in current dir)
docto-trace scan

# Scan a specific folder by ID
docto-trace scan --root-id 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms

# Limit traversal depth, show top 20 folders, write report to ./reports/
docto-trace scan --max-depth 5 --top 20 --output ./reports/

# Use a service account instead of OAuth2
docto-trace scan --service-account ./service_account.json

# Show all options
docto-trace scan --help

# Check version
docto-trace --version
```

### Example terminal output

```
🔐 Authenticating with Google Drive…
✅ Using cached token.

🔍 Scanning: My Drive
⠙ Traversing folders… [00:12]

══════════════════ 📦 Storage Overview ═══════════════════
  Root:          My Drive
  Total files:   14,832
  Total folders: 1,204
  Total size:    48.3 GB
  Max depth:     9

═══════════════ 🏆 Top 10 Largest Folders ════════════════
 Rank  Folder       Files    Size
 1     Projects     8,241    31.2 GB
 2     Archive      3,102    10.5 GB
 ...

✅ Report saved → output/report.json
```

---

## Report Schema

The output `report.json` follows the `HealthReport` Pydantic schema (schema version `0.1.0`):

```json
{
  "schema_version": "0.1.0",
  "generated_at": "2026-03-22T13:30:00Z",
  "storage_tree": { ... },
  "insights": {
    "top_folders": [...],
    "deep_folders": [...],
    "top_n": 10,
    "deep_folder_threshold": 5
  },
  "zombies": [],
  "duplicates": [],
  "action_plan": []
}
```

---

## Configuration

All settings can be overridden with environment variables prefixed `DOCTO_TRACE_`:

| Variable | Default | Description |
|---|---|---|
| `DOCTO_TRACE_CREDENTIALS_PATH` | `credentials.json` | OAuth2 credentials file |
| `DOCTO_TRACE_TOKEN_PATH` | `token.json` | Cached token path |
| `DOCTO_TRACE_SERVICE_ACCOUNT_PATH` | _(none)_ | Service account key path |
| `DOCTO_TRACE_MAX_DEPTH` | _(unlimited)_ | Max folder nesting to traverse |
| `DOCTO_TRACE_DEEP_FOLDER_THRESHOLD` | `5` | Depth to flag as "deep" |
| `DOCTO_TRACE_TOP_N` | `10` | Top-N largest folders |
| `DOCTO_TRACE_OUTPUT_DIR` | `output/` | Report output directory |
| `DOCTO_TRACE_PAGE_SIZE` | `1000` | Drive API items per page |

---

## Development

```bash
make install   # Install with dev dependencies
make lint      # Lint with ruff
make fix       # Auto-fix lint issues
make test      # Run unit tests (no credentials needed)
make typecheck # Run mypy
```

---

## Architecture

```
docto_trace/
├── cli.py                  # Typer root entry point
├── config.py               # Pydantic settings
├── auth/
│   ├── google_drive.py     # OAuth2 + service account flow
│   └── token_store.py      # Token serialization
├── connectors/
│   ├── base.py             # AbstractConnector interface
│   └── google_drive.py     # Drive API connector (async, paginated)
├── engine/
│   ├── traversal.py        # Async recursive tree builder
│   └── analytics.py        # Top-N, deep-folder analytics
├── schemas/
│   ├── storage.py          # FileNode, FolderNode, StorageTree
│   └── report.py           # HealthReport, InsightSummary, stubs
└── commands/
    ├── scan.py             # `docto-trace scan` command
    └── report.py           # `docto-trace report` (v0.2 stub)
```

---

## License

MIT © [Docto Studio](https://github.com/Docto-Studio)
