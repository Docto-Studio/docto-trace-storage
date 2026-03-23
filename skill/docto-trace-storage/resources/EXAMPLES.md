# Docto Trace — Annotated Example Reports

These condensed excerpts show what a real `report.json` looks like and how Claude
should interpret and respond to each section.

---

## Example 1 — Small Drive (clean)

```json
{
  "schema_version": "0.2.1",
  "generated_at": "2026-03-01T09:00:00Z",
  "storage_tree": {
    "root_name": "My Drive",
    "total_files": 421,
    "total_folders": 38,
    "total_size_bytes": 1287651328,
    "max_depth_reached": 4
  },
  "insights": {
    "top_folders": [
      { "name": "Documents", "path": "My Drive/Documents", "total_size_human": "800 MB", "file_count": 310, "depth": 1 },
      { "name": "Photos", "path": "My Drive/Photos", "total_size_human": "430 MB", "file_count": 111, "depth": 1 }
    ],
    "deep_folders": [],
    "top_n": 10,
    "deep_folder_threshold": 5
  },
  "zombies": [],
  "duplicates": [],
  "action_plan": []
}
```

**How to respond:**
> Your Drive is in great shape 🎉 — 421 files using ~1.2 GB total, no zombie files, no duplicates, and no deeply nested folders. The largest folder is **Documents** at 800 MB. Nothing to action right now.

---

## Example 2 — Medium Drive (some issues)

```json
{
  "schema_version": "0.2.1",
  "storage_tree": {
    "root_name": "My Drive",
    "total_files": 6840,
    "total_folders": 412,
    "total_size_bytes": 21474836480,
    "max_depth_reached": 7
  },
  "insights": {
    "top_folders": [
      { "name": "Projects", "path": "My Drive/Projects", "total_size_human": "14.3 GB", "file_count": 4100, "depth": 1 },
      { "name": "Archive", "path": "My Drive/Archive", "total_size_human": "5.8 GB", "file_count": 2200, "depth": 1 }
    ],
    "deep_folders": [
      { "name": "Archive", "path": "My Drive/Projects/2022/Q3/Internal/Drafts/Archive", "depth": 7, "file_count": 12 }
    ],
    "top_n": 10,
    "deep_folder_threshold": 5
  },
  "zombies": [
    { "file_id": "abc123", "name": "budget_draft_v1.xlsx", "path": "My Drive/Finance/budget_draft_v1.xlsx", "last_modified": "2021-06-15T00:00:00Z", "size_bytes": 524288, "reason": "stale" },
    { "file_id": "def456", "name": "meeting_notes_jan.docx", "path": "My Drive/Archive/meeting_notes_jan.docx", "last_modified": "2020-01-10T00:00:00Z", "size_bytes": 204800, "reason": "stale" }
  ],
  "duplicates": [
    {
      "fingerprint": "a1b2c3d4e5f6",
      "files": ["id1", "id2"],
      "file_names": ["client_brief.pdf", "client_brief_copy.pdf"],
      "file_paths": ["My Drive/Projects/client_brief.pdf", "My Drive/Archive/client_brief_copy.pdf"],
      "size_bytes_per_copy": 2097152,
      "wasted_bytes": 2097152
    }
  ],
  "action_plan": [
    { "severity": "warning", "category": "zombie", "description": "2 zombie files found (stale > 24 months). Consider archiving or deleting.", "affected_ids": ["abc123", "def456"] },
    { "severity": "info",    "category": "duplicate", "description": "1 duplicate group found wasting 2 MB.", "affected_ids": ["id1", "id2"] },
    { "severity": "info",    "category": "deep_folder", "description": "1 folder nested at depth 7 (threshold: 5).", "affected_ids": [] }
  ]
}
```

**How to respond:**
> Your Drive has **20 GB** across 6,840 files. Here's what I found:
>
> **🟡 Warnings**
> - **2 zombie files** (stale > 2 years): `budget_draft_v1.xlsx` (Jun 2021, 512 KB) and `meeting_notes_jan.docx` (Jan 2020, 200 KB). Total ≈ 712 KB — small but worth cleaning up.
>
> **🔵 Observations**
> - **1 duplicate group**: `client_brief.pdf` exists in both `Projects/` and `Archive/`. Wasted: 2 MB. Keep one, delete the other.
> - **1 deeply nested folder** at depth 7: `My Drive/Projects/2022/Q3/Internal/Drafts/Archive`. Consider flattening.
>
> **Biggest folder:** Projects at 14.3 GB — worth keeping an eye on.

---

## Example 3 — Large Drive (critical issues)

```json
{
  "schema_version": "0.2.1",
  "storage_tree": {
    "root_name": "My Drive",
    "total_files": 14832,
    "total_folders": 1204,
    "total_size_bytes": 51876044800,
    "max_depth_reached": 9
  },
  "insights": {
    "top_folders": [
      { "name": "Projects", "path": "My Drive/Projects", "total_size_human": "31.2 GB", "file_count": 8241, "depth": 1 },
      { "name": "Archive",  "path": "My Drive/Archive",  "total_size_human": "10.5 GB", "file_count": 3102, "depth": 1 }
    ],
    "deep_folders": [
      { "name": "Old Backups", "path": "My Drive/Projects/2019/…/Old Backups", "depth": 9, "file_count": 340 }
    ],
    "top_n": 10,
    "deep_folder_threshold": 5
  },
  "zombies": [
    { "name": "old_invoice.pdf", "path": "My Drive/Finance/old_invoice.pdf", "last_modified": "2020-01-15T10:30:00Z", "size_bytes": 2202009, "reason": "stale" }
  ],
  "duplicates": [
    {
      "fingerprint": "c8cd4fe0ab7a7fe8",
      "files": ["id1", "id2"],
      "file_names": ["8CDA554B.mov", "8CDA554B.mov"],
      "file_paths": ["My Drive/Backup/8CDA554B.mov", "My Drive/Photos/8CDA554B.mov"],
      "size_bytes_per_copy": 12582912,
      "wasted_bytes": 12582912
    }
  ],
  "action_plan": [
    { "severity": "critical", "category": "duplicate",    "description": "70 duplicate groups wasting 104 MB. Largest: video files in Backup vs Photos.", "affected_ids": [] },
    { "severity": "warning",  "category": "zombie",       "description": "381 zombie files (stale > 24 months), ~820 MB total.", "affected_ids": [] },
    { "severity": "info",     "category": "deep_folder",  "description": "3 folders nested at depth ≥ 8.", "affected_ids": [] }
  ]
}
```

**How to respond:**
> Your Drive holds **48 GB** across 14,832 files. There are some significant issues to address:
>
> **🔴 Critical**
> - **70 duplicate groups** wasting ~104 MB combined. The biggest single waste is `8CDA554B.mov` — a 12 MB video that's in both `Backup/` and `Photos/`. Recommend a deduplication pass starting with the largest groups.
>
> **🟡 Warnings**
> - **381 zombie files** (not modified in > 2 years), totalling ~820 MB. The oldest are in `Finance/`. These are candidates for archiving or deletion.
>
> **🔵 Observations**
> - **3 deeply nested folders** (depth ≥ 8), including `Old Backups` with 340 files buried 9 levels deep.
>
> **Recommended actions (in order of impact):**
> 1. Review and clean up the 70 duplicate groups — easy wins with the most files.
> 2. Archive or delete the 381 zombie files — frees up ~820 MB.
> 3. Reorganise deeply nested folders to improve discoverability.
