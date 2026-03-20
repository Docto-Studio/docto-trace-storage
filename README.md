# docto-trace-storage 🔍

**Map your data footprint. Kill the digital chaos.**

`docto-trace-storage` is a lightweight, open-source auditor designed to discover, visualize, and report the state of your company’s cloud storage. It identifies orphaned files, duplicates, and hidden "storage leaks" to prepare your organization for a **centralized memory** and AI-readiness.

This repository is part of the **Docto Trace** suite: tools built to audit and understand data infrastructure before taking action.

---

## Why this exists?
Standard cloud interfaces (Google Drive, OneDrive) are built to store, not to manage. They hide folder sizes, obscure duplicate data, and make it nearly impossible to audit large-scale file trees. `docto-trace-storage` brings visibility back to the admin.

## Key Features
* **Deep Folder Analytics:** Surface hidden large folders that native UIs won't show.
* **Zombie File Detection:** Identify files that haven't been accessed or modified in years.
* **Duplicate Discovery:** Find redundant copies wasting space and confusing your team.
* **AI-Readiness Report:** Export a clean JSON/CSV mapping of your data to decide what should be indexed for LLMs and what should be archived.

## Quick Start (Preview)

### Prerequisites
* Python 3.10+
* Cloud Provider API Credentials (OAuth2)

### Installation
```bash
pip install docto-trace-storage
```

### Supported Sources
* [x] Google Drive (In Progress)
* [ ] OneDrive (Planned)
* [ ] Amazon S3 (Planned)
* [ ] Dropbox (Planned)

## The Docto Vision
We believe companies shouldn't suffer from Digital Dementia. Our mission is to build the open-source ecosystem that turns scattered files from any source into a structured, centralized memory.

* **Trace:** Audit and map (You are here).
* **Form:** Organize and clean.
* **Flux:** Sync and move.
* **Echo:** Interact and remember.

## License
Licensed under the Apache License, Version 2.0. See the LICENSE file for more information.

Built with 🏗️ by Docto-Studio
