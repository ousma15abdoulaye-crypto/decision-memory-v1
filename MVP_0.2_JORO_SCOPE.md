# Decision Memory System — MVP 0.2 (JORO Scope)

## Status
FOUNDATIONAL DOCUMENT — NON-NEGOTIABLE  
This document defines the strict execution boundary of the MVP.  
Any feature, idea, or contribution that violates this scope MUST be rejected.

---

## Purpose (Why this exists)

The Decision Memory System exists to:

- Radically reduce cognitive load during real procurement work
- Allow decision memory to emerge passively from action
- Preserve organizational memory beyond individuals and turnover

This system MUST survive:
- its creator (Abdoulaye Ousmane)
- any single team, manager, or contributor
- any specific ERP, NGO, or institutional context

The tool is designed to be ERP-agnostic, organization-agnostic, and role-agnostic.

---

## What This System Is NOT

This system is explicitly NOT:

- a compliance tool
- an audit system
- a fraud detection mechanism
- a supplier evaluation or scoring engine
- a decision automation system
- a dashboard or KPI platform
- an ERP replacement
- a reporting tool for HQ or management

Any attempt to move the system in these directions is a violation of its core intent.

---

## MVP Scope — V1 / V0.2 (Frozen)

### Workflow
- Single workflow ONLY: **DAO Opening (Offers Reception & Opening)**
- JORO records offer deposits, withdrawals, and opening events
- One real DAO instance, end-to-end
- Field-level usage under pressure
- No multi-workflow support (RFQ logic, ITB analysis, contracts, etc.)

---

## Core Invariants (Must Never Be Broken)

These invariants apply now and forever:

1. Cognitive load must always be reduced, never increased
2. One action equals one screen
3. Memory is a by-product, never a task
4. Human decision is final and explicit
5. No judgement, no scoring, no ranking
6. No recommendations or suggestions
7. Usable without training
8. Offline-first by design
9. Append-only data (nothing is overwritten)
10. The system records reality as it happens — it does not correct it

If an idea violates even ONE invariant, it must be rejected.

---

## User Interface Constraint

- Exactly **3 screens**
- No additional views
- No dashboards
- No admin interface
- No configuration screens

---

## Screen Definitions

### Screen 1 — Start RFQ Case
Purpose: Capture the real initiation of an RFQ.

User inputs:
- RFQ title (free text, short)
- Request origin (who / where)
- Items list:
  - item name (free text)
  - quantity (as expressed by the requester)

Rules:
- No specifications
- No normalization
- No validation logic
- The system records what the user received, not what “should” exist

---

### Screen 2 — Collect Quotes
Purpose: Record supplier interactions as they occur.

User inputs per supplier:
- Supplier name (free text)
- Price per item (as stated)
- Optional total price
- Optional lead time
- Optional validity date

Rules:
- Quotes are recorded independently
- No comparison logic
- No ordering
- No highlighting of differences
- The system does not “analyze” quotes

---

### Screen 3 — Decide & Close
Purpose: Capture the human decision and next action.

User inputs:
- Chosen supplier (as decided in reality)
- Decision reason (raw human text)
- Next operational action taken (e.g. phone call, PO sent)

Rules:
- No rewriting
- No summarization
- No AI-assisted justification
- The wording remains human, imperfect, contextual

---

## Data Philosophy

- All records are append-only
- Corrections are new records, never edits
- Inconsistencies are preserved
- Ambiguity is allowed
- Memory emerges from accumulation, not optimization

---

## Explicitly Out of Scope (V1)

- Supplier scoring or ranking
- Automated recommendations
- Optimization logic
- Dashboards or analytics
- Compliance or audit features
- Fraud detection
- ERP integration
- Mandatory fields beyond the minimum
- Customization or configuration
- Multi-user roles or permissions

---

## Definition of Success (MVP)

Success is NOT:
- number of features
- data quality
- completeness
- sophistication

Success IS:
- a visible reduction in mental effort
- faster movement from quote collection to decision
- the tool being usable instinctively by a field user
- decision memory existing without asking for it

---

## Final Guardrail

If a future contributor asks:
“Can we add just one more thing?”

The default answer is:
NO.

This system survives by subtraction, not addition.
