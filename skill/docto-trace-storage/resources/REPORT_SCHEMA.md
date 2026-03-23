# Docto Trace — report.json Schema Reference

This document describes every field in the `HealthReport` JSON file produced by
`docto-trace scan`. Use this reference when interpreting a report or answering
questions about specific fields.

---

## Top-Level: `HealthReport`

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Always `"0.2.1"` for this release. |
| `generated_at` | `datetime (ISO 8601)` | When the report was produced. |
| `storage_tree` | `StorageTree` | Complete snapshot of the scanned Drive. |
| `insights` | `InsightSummary` | Structural analytics (top folders, deep nesting). |
| `zombies` | `ZombieFile[]` | Files flagged as stale or orphaned. Empty = none found. |
| `duplicates` | `DuplicateGroup[]` | Groups of files with identical content. Empty = none found. |
| `action_plan` | `ActionItem[]` | Ordered remediation recommendations. Empty = nothing to fix. |

---

## `StorageTree`

| Field | Type | Description |
|---|---|---|
| `root_id` | `string` | Drive ID of the scan root (e.g. `"root"` = My Drive). |
| `root_name` | `string` | Display name of the root folder (e.g. `"My Drive"`). |
| `tree` | `FolderNode` | Fully resolved recursive folder tree (can be very large). |
| `scanned_at` | `datetime` | When the traversal started. |
| `total_files` | `integer` | Total non-folder files discovered. |
| `total_folders` | `integer` | Total folder nodes discovered. |
| `total_size_bytes` | `integer` | Cumulative size of all files in bytes. |
| `max_depth_reached` | `integer` | Greatest folder nesting depth found during the scan. |

---

## `FolderNode`

Represents a single folder. The `children` array contains nested `FolderNode` and `FileNode` objects recursively.

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Google Drive folder ID. |
| `name` | `string` | Display name. |
| `children` | `(FileNode | FolderNode)[]` | Direct children (files + sub-folders). |
| `total_size_bytes` | `integer` | Cumulative size of all descendant files. |
| `total_file_count` | `integer` | Total descendant non-folder file count. |
| `depth` | `integer` | Nesting depth from the scan root (root = 0). |
| `parents` | `string[]` | Parent folder IDs. |
| `web_view_link` | `string \| null` | Browser link to open this folder in Drive. |

---

## `FileNode`

Represents a single non-folder file.

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Google Drive file ID. |
| `name` | `string` | Display name. |
| `mime_type` | `string` | MIME type as reported by Drive (e.g. `"application/pdf"`). |
| `size_bytes` | `integer` | File size in bytes. `0` for Google-native files (Docs, Sheets, Slides). |
| `created_at` | `datetime \| null` | Creation timestamp. |
| `modified_at` | `datetime \| null` | Last modification timestamp. |
| `owners` | `string[]` | Email addresses of the file's owners. |
| `parents` | `string[]` | Parent folder IDs. |
| `web_view_link` | `string \| null` | Shareable browser link. |
| `depth` | `integer` | Nesting depth from the scan root. |
| `md5_checksum` | `string \| null` | MD5 from Drive API. `null` for Google-native formats. |
| `quota_bytes_used` | `integer` | Bytes charged against Google Storage quota (`quotaBytesUsed`). Non-zero for Google Docs/Sheets/Slides where `size_bytes` is 0. |
| `effective_size_bytes` | `integer` _(computed)_ | Best available size: `size_bytes` for binary files; `quota_bytes_used` for Google-native files. **Use this for all size calculations.** |

---

## `InsightSummary`

| Field | Type | Description |
|---|---|---|
| `top_folders` | `FolderInsight[]` | Top-N largest folders by cumulative size. |
| `deep_folders` | `FolderInsight[]` | Folders whose depth ≥ `deep_folder_threshold`. |
| `top_n` | `integer` | The N used to compute `top_folders`. |
| `deep_folder_threshold` | `integer` | Depth cutoff for "deep" classification (default: 5). |

### `FolderInsight` (flattened folder view)

| Field | Type | Description |
|---|---|---|
| `folder_id` | `string` | Drive ID. |
| `name` | `string` | Display name. |
| `path` | `string` | Human-readable breadcrumb path from scan root (e.g. `"My Drive/Projects/Q1"`). |
| `depth` | `integer` | Nesting depth. |
| `total_size_bytes` | `integer` | Cumulative descendant file size. |
| `total_size_human` | `string` | Human-readable size (e.g. `"3.2 GB"`). |
| `file_count` | `integer` | Number of descendant files. |

---

## `ZombieFile`

| Field | Type | Description |
|---|---|---|
| `file_id` | `string` | Drive ID. |
| `name` | `string` | Display name. |
| `path` | `string` | Breadcrumb path from scan root. |
| `last_modified` | `datetime \| null` | Last modification timestamp. |
| `size_bytes` | `integer` | File size (0 for Google-native). |
| `web_view_link` | `string \| null` | Browser link to open the file. |
| `reason` | `"stale" \| "orphaned"` | Why it was flagged: `stale` = not modified in > N months; `orphaned` = no parent folder found. |

---

## `DuplicateGroup`

| Field | Type | Description |
|---|---|---|
| `fingerprint` | `string` | Content identity key: MD5 checksum for binary files; `"<size>:<normalized_name>"` for Google-native files. |
| `files` | `string[]` | Drive IDs of the duplicate copies. |
| `file_names` | `string[]` | Display names (same order as `files`). |
| `file_paths` | `string[]` | Breadcrumb paths (same order as `files`). |
| `size_bytes_per_copy` | `integer` | Size of a single copy. |
| `wasted_bytes` | `integer` | Bytes consumed by redundant copies (`total_size - 1 copy`). |

**Deduplication strategy:**
- Binary files (PDFs, images, Office docs): primary key is `md5Checksum` from the Drive API.
- Google-native files (Docs, Sheets, Slides): Drive does not provide MD5; fallback key is `"<size_bytes>:<normalized_name>"`.

---

## `ActionItem`

| Field | Type | Description |
|---|---|---|
| `severity` | `"critical" \| "warning" \| "info"` | Priority level. |
| `category` | `string` | Type of issue: `"zombie"`, `"duplicate"`, `"deep_folder"`. |
| `description` | `string` | Human-readable description of the recommended action. |
| `affected_ids` | `string[]` | Drive IDs of files/folders involved (may be empty). |
