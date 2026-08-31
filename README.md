# Arbiter

### Trust-Aware Revenue Negotiation for Agentic Commerce

Arbiter is a trust-aware agentic commerce system where a **buyer AI agent** and a **merchant AI agent** negotiate a purchase autonomously — while the merchant retains deterministic control over how much autonomy and discount authority the buyer is allowed to receive.

The goal is not simply to make AI negotiate and pay.

**Arbiter answers a harder question:**

> **How much autonomy should this buyer's agent be given, and what is the most profitable safe deal right now?**

Arbiter combines buyer trust, deterministic merchant policies, an autonomy budget, and dynamic offer optimization through a centralized **Negotiation Decision Controller (NDC)**.

---

## Core Idea

Arbiter follows one fundamental principle:

**Dynamic intelligence can optimize only inside hard deterministic boundaries.**

The Dynamic Offer Engine can recommend a better deal, but it can never exceed:

* the merchant's maximum discount ceiling
* the remaining negotiation budget
* the buyer's allowed authority tier
* any policy or safety restrictions

The **Negotiation Decision Controller** is the single source of truth for these decisions.

---

## Architecture

```text
                    ┌──────────────────────┐
                    │     Buyer Agent      │
                    │  Purchase / Offers   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Seller Growth      │
                    │       Agent          │
                    └──────────┬───────────┘
                               │
                         Proposed Offer
                               │
                               ▼
              ┌─────────────────────────────────┐
              │ Negotiation Decision Controller │
              │              (NDC)               │
              └───────────────┬─────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ Trust Score│    │   Bounds   │    │   Budget   │
     │   Engine   │    │   Engine   │    │   Manager  │
     └────────────┘    └────────────┘    └────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Dynamic Offer    │
                    │     Engine       │
                    └────────┬─────────┘
                             │
                       Final Decision
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
           APPROVE        RESTRICT        BLOCK
              │
              ▼
       Payment Execution
              │
              ▼
        Audit Trail
```

---

## Key Components

### Buyer Agent

A simulated buyer-side AI agent that represents different negotiation behaviors.

It can demonstrate:

* cooperative buyers
* price-sensitive buyers
* aggressive negotiators
* suspicious behavior
* adversarial policy-override attempts

---

### Seller Growth Agent

The merchant-facing AI agent responsible for conducting the negotiation.

The Seller Growth Agent **cannot independently authorize discounts or payments**.

Every proposed final offer must pass through the Negotiation Decision Controller.

---

### Buyer Trust Score Engine

Produces a transparent **0–100 trust score** using configurable signals such as:

* identity confidence
* intent confidence
* transaction history
* policy violations
* negotiation behavior

Example weighted formulation:

```text
Trust =
    0.30 × identity
  + 0.25 × intent
  + 0.20 × history
  + 0.15 × (1 - violation_rate)
  + 0.10 × behavior
```

Trust determines the buyer's negotiation authority.

Example tiers:

| Trust Score | Authority              |
| ----------- | ---------------------- |
| 80–100      | Full negotiation range |
| 40–79       | Restricted negotiation |
| < 40        | Block                  |

---

### Verification & Bounds Engine

The deterministic safety layer.

It enforces the merchant's **hard maximum discount ceiling** and detects policy violations.

For example:

```text
Merchant maximum discount = 12%

No other component may authorize:
13%
15%
20%
...
```

Even if the Dynamic Offer Engine recommends a larger discount, the Controller clamps it to the hard ceiling.

---

### Autonomy Budget Manager

Controls the total amount of merchant value that can be given away over a configured period.

It tracks:

```text
Allocated Budget
       ↓
Used Budget
       ↓
Remaining Budget
```

This prevents the agent from making individually reasonable offers that collectively give away too much value.

Redis is used for fast, atomic budget accounting, with PostgreSQL providing persistent records.

---

### Dynamic Offer Engine

Computes the best offer inside the allowed constraints.

It considers factors such as:

* buyer trust
* merchant discount ceiling
* remaining budget
* product margin
* inventory
* estimated conversion probability

The engine is intentionally implemented as an **explainable heuristic**, rather than being presented as a trained ML model.

Its output is always clamped by the hard constraints.

```text
Recommended Offer
        ↓
min(
    recommended_offer,
    bounds_ceiling,
    budget_limit
)
        ↓
Authorized Offer
```

---

### Negotiation Decision Controller

The NDC is the central orchestration and decision-making layer.

For every proposed offer it evaluates:

```text
1. Trust Score
       ↓
2. Verification & Bounds
       ↓
3. Autonomy Budget
       ↓
4. Dynamic Offer
       ↓
5. Hard Constraint Clamp
       ↓
6. Final Decision
       ↓
7. Audit Log
```

Possible decisions:

* **Approve**
* **Counter**
* **Restrict**
* **Block**

The Controller is the **only component authorized to issue the final negotiation decision**.

---

## End-to-End Flow

```text
Buyer Agent
    │
    │ Purchase Intent
    ▼
Seller Growth Agent
    │
    │ Proposed Offer
    ▼
Negotiation Decision Controller
    │
    ├──► Trust Score
    │
    ├──► Bounds Check
    │
    ├──► Budget Check
    │
    └──► Dynamic Offer
             │
             ▼
       Hard Constraint Clamp
             │
             ▼
       Final Decision
             │
       ┌─────┼─────┐
       ▼     ▼     ▼
    Approve Restrict Block
       │
       ▼
Razorpay Test Payment
       │
       ▼
Transaction + Audit Trail
```

---

## Technology Stack

| Layer                 | Technology                    |
| --------------------- | ----------------------------- |
| Backend / Controller  | Python, FastAPI               |
| Database              | PostgreSQL                    |
| Budget State          | Redis                         |
| Buyer / Seller Agents | LLM + structured tool calling |
| Payment               | Razorpay Test API             |
| Frontend              | Next.js, React                |
| Styling               | Tailwind CSS                  |
| Charts                | Recharts                      |
| Migrations            | Alembic                       |
| Containers            | Docker Compose                |
| Synthetic Data        | Python / Faker                |

---

## Data Model

The core relational entities include:

```text
Buyer
Merchant Policy
Trust Score Record
Budget Ledger
Transaction
Audit Log
```

The audit trail captures the decision context, including:

* trust score
* bounds applied
* budget state
* computed offer
* final decision
* reasoning
* transaction information

This creates a traceable record of why an autonomous commerce decision was made.

---

## Safety Model

Arbiter intentionally separates **hard constraints** from **soft optimization signals**.

```text
                 HARD CONSTRAINTS
              ┌─────────────────────┐
              │ Merchant Policy     │
              │ Discount Ceiling    │
              │ Budget Limit        │
              │ Policy Violations   │
              └──────────┬──────────┘
                         │
                         ▼
                Allowed Decision Space
                         │
                         ▼
              ┌─────────────────────┐
              │  Dynamic Intelligence│
              │                     │
              │ Trust + Optimization│
              └──────────┬──────────┘
                         │
                         ▼
                  Best Safe Offer
```

**Optimization never gets to redefine the boundary.**

---

## Project Status

Arbiter is being developed as a rapid end-to-end prototype for the **Razorpay Buildathon**.

## Design Principles

### 1. Hard bounds always win

No optimizer, agent, or LLM can override merchant-defined safety constraints.

### 2. The Controller is the source of truth

Agents do not make independent authorization decisions.

### 3. Trust controls autonomy

A buyer's behavior influences how much negotiation authority it receives.

### 4. Optimization happens inside the safe zone

The system searches for the best profitable deal only after establishing the allowed decision space.

### 5. Every decision is explainable

Negotiation outcomes should be inspectable through the audit trail.

### 6. Start deterministic, evolve later

The Trust Score and Dynamic Offer Engine use transparent formulas and heuristics rather than pretending to be ML systems without appropriate training data.

---

## Future Work

Potential future extensions include:

* trained conversion-probability models
* richer fraud signals
* production KYC integration
* advanced buyer lifetime-value optimization
* multi-product bundling optimization
* more sophisticated negotiation policies
* production-scale distributed deployment

A trained conversion model is intentionally outside the initial hackathon scope because it requires appropriate elasticity data.

---

## Project Structure

```text
Arbiter/
├── client/
├── server/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

The repository is intentionally structured as a **single monorepo** containing the complete Arbiter application.

---

## Why Arbiter?

Traditional agentic commerce focuses on enabling agents to **negotiate and transact**.

Arbiter focuses on the decision between those two actions:

> **Should this agent be trusted with this deal, and what is the maximum economically sensible autonomy to give it?**

That makes trust, safety, autonomy, and revenue optimization part of the same decision loop.

---

## Built for Agentic Commerce

**Arbiter — Trust-Aware Revenue Negotiation**
