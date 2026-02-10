# DMS Architecture — Couche A / Couche B

## Overview

DMS uses a two-layer architecture with strict firewall between them.

### Couche A — Procurement Worker
Handles the operational procurement workflow:
- Document deposit (PDF, DOCX, XLSX)
- Automatic extraction & pre-analysis
- Business rules engine (scoring)
- CBA export (Excel multi-tab)
- PV generation (DOCX)
- Committee review workflow

### Couche B — Market Memory
Append-only market intelligence layer:
- Canonical vendor/item/unit/geo registries with aliases
- Market signals (price observations) — append-only, corrections via `superseded_by`
- Price statistics & trend analysis

## Data Flow

```
[Document Upload] → Couche A (extraction → scoring → CBA → PV)
                           ↓ (after committee validation only)
                     [Outbox Event]
                           ↓
                     [Worker] → POST /api/market-signals → Couche B
```

## Database Schemas

### Couche A Tables
- `cases` — Procurement cases
- `lots` — Case lots
- `submissions` — Vendor submissions
- `submission_documents` — Uploaded files
- `preanalysis_results` — Extraction results
- `cba_exports` — CBA versions
- `minutes_pv` — PV documents
- `outbox_events` — Pending signals for Couche B

### Couche B Tables
- `vendors` / `vendor_aliases` / `vendor_events`
- `items` / `item_aliases`
- `units` / `unit_aliases`
- `geo_master` / `geo_aliases`
- `market_signals` (append-only)

### System Tables
- `audit_logs` (append-only)
