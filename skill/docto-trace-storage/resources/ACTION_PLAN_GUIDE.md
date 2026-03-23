# Docto Trace — Action Plan Interpretation Guide

This guide helps Claude interpret `action_plan` items from a Docto Trace `report.json`
and formulate clear, prioritised recommendations for users.

---

## Severity Levels

| Severity | Icon | Meaning | When to surface first |
|---|---|---|---|
| `critical` | 🔴 | Significant storage waste or data health risk | Always lead with these |
| `warning` | 🟡 | Potential issue; worth addressing | Second priority |
| `info` | 🔵 | Informational observation; no urgent action | Mention last or omit if response is long |

Always sort `critical` → `warning` → `info` when presenting the action plan.

---

## Categories

### `duplicate`

**What it means:** Multiple copies of the same content exist, wasting quota.

**How to communicate:**
- Tell the user how many groups were found and the total wasted bytes.
- Highlight the top 3 groups by wasted bytes (largest waste first).
- Suggest keeping the copy in the most logical folder and deleting the rest.
- Remind them the CLI is read-only — they must delete manually in Drive or via Google Drive app.

**Example conversation flow:**
> "You have 70 duplicate groups wasting ~104 MB. The biggest offender is `8CDA554B…mov` (12 MB wasted) which appears in both `My Drive/Backup/` and `My Drive/Photos/`. I'd recommend keeping the one in Photos and removing the Backup copy."

---

### `zombie`

**What it means:** Files that haven't been modified in longer than the configured threshold (default: 24 months).

**How to communicate:**
- State the count and cumulative size.
- Group by age bracket if there are many (e.g., "5 files not touched since 2019, 23 files since 2021").
- Suggest archiving or deleting via Google Drive. If the files have `web_view_link`, offer to list them.
- Avoid being alarmist — zombie status is about *staleness*, not corruption.

**Example conversation flow:**
> "I found 381 zombie files (files not modified in over 2 years), totalling ~820 MB. The oldest is `old_invoice.pdf` last modified in January 2020. Consider archiving these to Google Drive's Archive folder or deleting files you no longer need."

---

### `deep_folder`

**What it means:** Folders nested beyond the configured depth threshold (default: 5 levels).

**How to communicate:**
- State which folders are deeply nested and their depth.
- Explain that deep nesting makes files hard to find and can slow traversal.
- Suggest flattening the structure by consolidating sub-folders.

**Example conversation flow:**
> "3 folders are nested 8+ levels deep. Deep nesting makes files hard to discover. Consider reorganising `My Drive/Projects/2023/Q1/Internal/Drafts/Archive/` into a flatter structure."

---

## General Response Template

When composing a full Drive health response, use this structure:

```
### Your Google Drive Health Summary

**Overview:** X files · Y GB total · scanned Z minutes ago

**🔴 Critical Issues**
- [List critical action_plan items]

**🟡 Warnings**
- [List warning severity items]

**🔵 Observations**
- [List info severity items — or omit if none]

**Top Largest Folders**
[Table: rank, name, path, size]

**Recommended Next Steps**
1. [Most impactful action first]
2. ...
```

---

## What Claude Can and Cannot Do

| Can | Cannot |
|---|---|
| Explain what was found | Delete, move, or rename files |
| Prioritise cleanup recommendations | Trigger a scan without the Skill scripts |
| List specific files by path | Access Drive directly (without the CLI) |
| Re-analyse the report for follow-up questions | Modify the report.json |
| Run a fresh scan via `run_scan.py` | Write to Google Drive (read-only by design) |
