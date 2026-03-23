# Docto Trace Skill — Admin Deployment Guide

This guide is for **Team/Enterprise admins** who want to provision the
Docto Trace Storage Auditor Skill to their organisation in Claude.

---

## What This Skill Does

Allows Claude to **actively scan and audit a user's Google Drive** — detecting zombie files,
duplicate content, and storage waste — without the user needing to touch the terminal.
The Skill invokes the open-source `docto-trace-storage` CLI under the hood.

**Privacy guarantees:**
- Read-only OAuth2 scopes only (`drive.readonly`, `drive.metadata.readonly`)
- All execution is local on the user's machine — no data passes through any external servers
- The Skill does not store or transmit any Drive data

---

## Prerequisites

Each user who activates the Skill must have:
- Python 3.10+ installed
- `docto-trace-storage` installed: `pip install docto-trace-storage`
- A Google account with access to the Drive they want to scan

---

## Packaging the Skill

```bash
cd skill/

# The ZIP must have the skill folder as the root, not files directly at root
zip -r docto-trace-storage.zip docto-trace-storage/

# Verify the structure
unzip -l docto-trace-storage.zip
```

Expected output (the Skill folder must be the root inside the ZIP):
```
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  xx-xx-xxxx xx:xx   docto-trace-storage/
     ...                      docto-trace-storage/SKILL.md
     ...                      docto-trace-storage/resources/REPORT_SCHEMA.md
     ...                      docto-trace-storage/resources/COMMANDS_REFERENCE.md
     ...                      docto-trace-storage/resources/ACTION_PLAN_GUIDE.md
     ...                      docto-trace-storage/resources/EXAMPLES.md
     ...                      docto-trace-storage/scripts/requirements.txt
     ...                      docto-trace-storage/scripts/run_scan.py
     ...                      docto-trace-storage/scripts/analyze_report.py
```

---

## Uploading to Claude

1. Go to [claude.ai/customize/skills](https://claude.ai/customize/skills)
2. Click **Upload Skill**
3. Select `docto-trace-storage.zip`
4. Confirm the Skill name: **Docto Trace — Storage Auditor**
5. Enable the Skill

**For organisation-wide provisioning (Team/Enterprise):**
- Go to **Admin → Customize → Skills**
- Upload the ZIP
- Set **Provisioning**: All users OR specific groups
- Enable **Auto-install** if you want it activated for everyone by default

See Anthropic's official guide:
[Provision and manage Skills for your organization](https://support.claude.com/en/articles/13119606-provision-and-manage-skills-for-your-organization)

---

## Testing After Upload

1. Enable the Skill in your account
2. Start a new Claude conversation
3. Try: **"Scan my Google Drive and tell me what's wasting space"**
4. Verify Claude:
   - Checks if `docto-trace` is installed
   - Runs `scripts/run_scan.py`
   - Calls `scripts/analyze_report.py`
   - Returns a structured storage health summary

For a quick sanity check without a real scan:
5. Try: **"Analyse this Drive report"** and paste one of the examples from `resources/EXAMPLES.md`

---

## Updating the Skill

When a new version of `docto-trace-storage` is released:
1. Update `scripts/requirements.txt` to the new version
2. Update any changed flags in `SKILL.md` and `resources/COMMANDS_REFERENCE.md`
3. Re-package and re-upload the ZIP

---

## Roadmap: Plugin (v0.3) and MCP Connector (v0.4)

| Phase | What ships |
|---|---|
| **v0.3 Plugin** | Cowork Plugin manifest + `/drive-audit` slash-command form |
| **v0.4 MCP Connector** | `docto-trace-mcp` server — live Drive queries from Claude without full scans |

These phases are tracked in the [docto-trace-storage GitHub repository](https://github.com/Docto-Studio/docto-trace-storage).
