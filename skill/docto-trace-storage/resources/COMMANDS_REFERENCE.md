# Docto Trace — CLI Commands Reference

Full flag reference for the `docto-trace` CLI (v0.2.0).
Use this when composing or explaining `run_scan.py` arguments, or when guiding users
through the CLI manually.

---

## `docto-trace --version` / `-v`

```bash
docto-trace --version   # → docto-trace-storage v0.2.0
docto-trace -v
```

---

## `docto-trace setup`

Interactive 4-step wizard to create your own Google Cloud project and OAuth2 credentials.
Run once for full control over the GCP registration.

```bash
docto-trace setup
docto-trace setup --output ~/my-creds.json
```

**When to recommend:** User wants to use their own GCP project / credentials instead of the
bundled Docto credentials.

---

## `docto-trace login`

Authenticate with Google Drive and cache the token locally. Subsequent commands reuse the
cached token silently.

```bash
docto-trace login
docto-trace login --credentials ./my-credentials.json
docto-trace login --service-account ./sa-key.json   # no browser flow
```

| Flag | Description |
|---|---|
| `--credentials PATH` | OAuth2 credentials JSON (default: bundled Docto credentials) |
| `--service-account PATH` | Service account key JSON (skips browser OAuth2 flow) |

**When to run:** Before the first `scan`, or after `logout`, or when the token expires.

---

## `docto-trace logout`

Delete the cached token. The next `scan` or `login` will trigger a fresh browser flow.

```bash
docto-trace logout
docto-trace logout --revoke   # also revoke on Google's servers
```

---

## `docto-trace scan` ← core command

Traverses Google Drive, runs all audits, and produces `report.json`.

```bash
# Full scan with defaults (My Drive, unlimited depth, top 10, 24-month zombie threshold)
docto-trace scan

# Narrow to a specific folder by Drive ID
docto-trace scan --root-id 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms

# Custom depth, top 20, custom output directory
docto-trace scan --max-depth 5 --top 20 --output ./reports/

# Flag files not modified in 12 months as zombies (default: 24)
docto-trace scan --stale-threshold 12

# Use your own credentials
docto-trace scan --credentials ./my-credentials.json

# Use a service account (no browser flow)
docto-trace scan --service-account ./sa-key.json
```

### Full flag table

| Flag | Short | Default | Description |
|---|---|---|---|
| `--root-id` | `-r` | `root` | Drive folder ID to start from (`root` = My Drive) |
| `--max-depth` | `-d` | unlimited | Max folder depth to traverse |
| `--top` | `-n` | `10` | Top-N largest folders to include |
| `--deep-threshold` | — | `5` | Depth to flag a folder as "deep" |
| `--stale-threshold` | `-S` | `24` | Months without modification = zombie file |
| `--credentials` | `-c` | bundled | Path to OAuth2 credentials JSON |
| `--output` | `-o` | `output/` | Directory where `report.json` is written |
| `--service-account` | `-s` | _(none)_ | Service account key path (skips browser) |

### Environment variable overrides

All flags can also be set via environment variables prefixed `DOCTO_TRACE_`:

| Variable | Default |
|---|---|
| `DOCTO_TRACE_CREDENTIALS_PATH` | `credentials.json` |
| `DOCTO_TRACE_TOKEN_PATH` | `token.json` |
| `DOCTO_TRACE_SERVICE_ACCOUNT_PATH` | _(none)_ |
| `DOCTO_TRACE_MAX_DEPTH` | _(unlimited)_ |
| `DOCTO_TRACE_DEEP_FOLDER_THRESHOLD` | `5` |
| `DOCTO_TRACE_TOP_N` | `10` |
| `DOCTO_TRACE_STALE_THRESHOLD_MONTHS` | `24` |
| `DOCTO_TRACE_OUTPUT_DIR` | `output/` |
| `DOCTO_TRACE_PAGE_SIZE` | `1000` |

---

## `docto-trace report`

_(Planned for v0.3)_ Extended reporting — owner analysis, sharing audit, cost estimation.
Not yet available. If the user asks, acknowledge it's on the roadmap.
