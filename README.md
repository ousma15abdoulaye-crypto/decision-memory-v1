# Decision Memory System — V1

## Purpose
This system is designed to reduce cognitive load in procurement decision-making
and allow decision memory to emerge naturally from real operational usage.

It does **not** aim to:
- improve the intrinsic “quality” of decisions
- replace human judgment
- optimize procurement outcomes

Its sole purpose is to **restore human decision capacity under operational pressure**.

---

## What This System Is NOT
This system is NOT:
- a compliance tool
- an audit system
- a fraud detection system
- a supplier scoring or ranking engine
- a decision automation system
- a system of record
- a replacement for ERP or official procurement platforms

It is a **complementary cognitive support layer**, not an institutional authority.

---

## Scope — V1 (Strict and Non-Negotiable)
- ONE single procurement process instance per execution scope (never mixed, never combined)
- Maximum **three (3) user screens**
- One real procurement case, end-to-end
- Designed for **field-level usage under pressure**
- No configuration and no customization in V1

Anything outside this scope is **explicitly out of V1**.

---

## Execution Scopes (Frozen)

This repository may contain one or more **frozen execution scope documents**.
Each scope defines exactly **what is built**, **what is forbidden**, and **what must not evolve**.

Examples:
- **MVP 0.2 — JORO (DAO Offer Reception & Opening Journal):**
  see `MVP_0.2_JORO_SCOPE.md`

- (Optional / future) **RFQ single-workflow execution:**
  see dedicated execution scope document

Execution scopes may evolve over time.
Execution scopes evolve only by explicit versioning (e.g. V0.2 → V0.3), never by silent modification.

**The constitutional invariants in this README override all implementations.**

---

## Core Invariants (Foundational — Non-Negotiable)
These invariants define the identity of the system. Violating any of them invalidates the product.

- Cognitive load must always be **reduced**, never increased
- One user action equals **one screen**
- Memory is a **by-product**, never a task
- Human decision is always final
- No judgment, no scoring, no ranking
- Usable without training
- Offline-first by design
- Append-only data model (no deletion — corrections occur by addition)
- Every recorded fact must be traceable to a **real operational action**

---

## Explicitly Forbidden — V1
The following are strictly forbidden in V1:
- Supplier scoring, ranking, or comparative metrics
- Automated recommendations or decision suggestions
- Dashboards, KPIs, analytics, or HQ reporting
- Compliance, audit, or fraud-detection features
- Multi-workflow complexity
- Any data entry whose sole purpose is reporting or documentation
- ERP dependency or tight coupling with any system of record
- Optimization logic of any kind

If a feature “seems useful” but violates these rules, it is **out of scope**.

---

## Goal of V1
Produce a **tangible and observable reduction of cognitive effort**
for a real user, in a real procurement situation.

Success is demonstrated when:
- the user completes the task faster
- with less mental fatigue
- without training
- without explanation
- and without altering their decision authority

If the system requires explanation, it has already failed.

---

## Foundational Principle
This system does not teach people how to decide.
It removes what prevents them from deciding.

Decision memory is not collected. It **emerges**.

---

## Survivability Clause
This system must survive:
- its creator (Abdoulaye Ousmane)
- any individual contributor
- any manager or sponsor
- any organizational restructuring

The vision, invariants, and purpose are **above all implementations**.

Code may evolve. Technology may change. These principles must not.
