# Next Steps

## Current Goal
Implement Training Sandbox Degradation Mode for Decision Hub.

## What needs to be done
1. Propose degradation plan (no code changes yet)
2. Identify 5 initial controlled degradations:
   - idempotency becomes non-obvious
   - status machine scattered
   - duplicated rule in payment + decision
   - broken correlation-id
   - API contract divergence

## Constraints
- Do NOT break entire system
- Keep system analyzable
- Keep it realistic (bank-like system)

## Expected Output
- Degradation plan
- Mapping to analyst skills
- Detection strategies

## Next Action
Ask Claude to:
- analyze current codebase
- propose degradation plan ONLY (no changes yet)


You are now working in a repository called `sa-lab-training`.

This repository is NOT production.
This repository is NOT the reference architecture.
This repository is a controlled educational copy of the original Decision Hub sandbox.

Your working mode: TRAINING SANDBOX DEGRADATION MODE

The goal is NOT random destruction.
The goal is controlled degradation of a realistic banking system so that a system analyst can:
- find the problem
- explain the problem
- reconstruct correct documentation from imperfect implementation
- identify anti-patterns
- propose a correction

This repository must remain:
- realistic
- analyzable
- structured enough for reverse engineering
- suitable for senior-level grading

Do NOT turn it into a broken mess.
Do NOT fully destroy architecture.
Do NOT delete half of the project.
Do NOT introduce chaotic nonsense.
Do NOT create toy mistakes.
Do NOT overcomplicate infrastructure.

The result must still look like a real banking sandbox similar to the original Decision Hub reference project.

═══════════════════════════════════════════════════════════════════════
PART 1 — PROJECT CONTEXT
═══════════════════════════════════════════════════════════════════════
This project is based on the original Decision Hub training/reference architecture.

Original architecture intent:
- api-gateway owns routing, correlation propagation, and no business logic;
- payment-service owns Transfer entity, lifecycle, idempotency, and orchestration;
- decision-hub owns rules, decision evaluation, explainability, and audit trail;
- ledger-mock owns posting simulation only.

Original target behavior includes:
- API-first contracts,
- explicit state transitions,
- idempotency,
- correlation-id propagation,
- structured error handling,
- explainability,
- AS-IS vs TO-BE comparison.

In the training version, these principles must be intentionally degraded in controlled ways.

═══════════════════════════════════════════════════════════════════════

PART 2 — TRAINING OBJECTIVE
═══════════════════════════════════════════════════════════════════════

This repository is used for Decision Hub Grading.

The candidate is expected to:
- read code and infer system behavior
- reconstruct architecture and logic
- identify ownership violations
- identify broken idempotency / retry behavior
- identify state-machine problems
- identify API-contract divergence
- identify observability gaps
- restore proper documentation
- answer backend-oriented questions relevant to this exact project

This is a senior-oriented grading sandbox.
Do not optimize for junior simplicity.
However, keep all flaws explainable and diagnosable.

═══════════════════════════════════════════════════════════════════════

PART 3 — DEGRADATION PRINCIPLES (MANDATORY)
═══════════════════════════════════════════════════════════════════════

All degradation must be CONTROLLED.
Every flaw must become a learning asset, not just damage.
1. WHAT exactly was changed
2. WHAT anti-pattern or engineering smell was created
3. WHAT analyst skill this tests
4. HOW it can be discovered in:
   - code,
   - flow,
   - logs,
   - API contracts,
   - database/state model

This is mandatory.
Every flaw must become a learning asset, not just damage.
═══════════════════════════════════════════════════════════════════════
PART 4 — STRICT WORKFLOW (follow exactly)
═══════════════════════════════════════════════════════════════════════
Before modifying any code, you MUST do only this:

Step 1.  Inspect repository
Step 2.  Propose degradation plan
Step 3.  Propose exact files to change (Map proposed changes to analyst skills)
Step 4.  Propose candidate README.md structure 
Step 5.  Propose facilitator hidden file structure
Step 6.  WAIT FOR APPROVAL ← do not proceed without this
Step 7.  Implement only approved flaws
Step 8.  Show which files are likely to be changed
Step 9. Explain why each change is useful for grading
Step 10.  Update README.md
Step 11.  Create hidden facilitator notes
Step 12. Summarize all changes
Step 13. Recommend the first wave of implementation

RULE: Do NOT modify any code until Step 6 approval is received.
Do NOT modify code until the plan is shown first.

═══════════════════════════════════════════════════════════════════════
PART 5 — FIRST WAVE: 5 MANDATORY FLAWS
═══════════════════════════════════════════════════════════════════════

Implement the first wave around exactly these 5 flaws (in this priority order):

FLAW 1: Idempotency made non-obvious
  The idempotency check must still exist but be placed AFTER a side effect
  (e.g., the transfer record is created in DB before the idempotency key is checked).
  The system still works in happy path but is broken on retry.
  Tests: idempotency thinking, retry safety, lifecycle reading.

FLAW 2: Status machine scattered across files
  Transfer status transitions must be assigned in at least 3 different files
  instead of in one authoritative place.
  No single file shows the complete picture.
  Tests: state machine reconstruction, source-of-truth ownership.

FLAW 3: Reject rule duplicated in two services (One reject rule duplicated in payment-service and decision-hub)
  One business rule (e.g., country blocklist or daily limit)
  must exist in BOTH payment-service AND decision-hub.
  The two implementations are slightly inconsistent (different threshold or field name).
  Tests: service ownership, decision logic scattering, explainability.

FLAW 4: Correlation-id propagation broken in one service
  In exactly ONE downstream call (payment-service → decision-hub OR → ledger-mock),
  the X-Correlation-Id must NOT be forwarded correctly.
  The call still works, but correlation is lost for that leg.
  Tests: observability thinking, log tracing, distributed request flow.

FLAW 5: API contract diverges from runtime behavior
  In exactly ONE endpoint, the OpenAPI contract must differ from what the code actually does.
  Examples: a field documented as required that the code treats as optional;
  an error code documented that is never actually returned;
  a field name in response that differs by underscore/camelCase.
  Tests: API-first discipline, contract vs implementation verification.

These five must be implemented first because they directly test:
- flow reading,
- lifecycle reconstruction,
- service ownership,
- observability thinking,
- API-first discipline.

═══════════════════════════════════════════════════════════════════════
PART 6 — FLAW CATALOG FOR FUTURE WAVES
═══════════════════════════════════════════════════════════════════════

You may introduce flaws only in realistic categories below.
Use this as the canonical library for waves 2 and 3 (do not implement now):

A. Logic flaws:
  - decision logic partially moved back into payment-service
  - one rule checked in two places with different behavior
  - inconsistent approve/reject paths
  - partial failure handled incorrectly
  - reject reason produced in non-centralized way
Possible examples:
- decision logic partially moved back into payment-service;
- one rule checked in two places;
- inconsistent approve/reject paths;
- one edge case is not covered;
- partial failure is handled incorrectly;
- reject reason is produced in a non-centralized way.


B. Data / state flaws:
  - one status assigned in more than one place
  - source of truth is not obvious
  - payment state and audit state may diverge
  - transition ownership is unclear
Possible examples:
- status machine is implicit and spread across several files;
- one status is assigned in more than one place;
- source of truth is not obvious;
- payment state and audit state may diverge;
- transition ownership is unclear.

C. API / contract flaws:
  - incomplete error responses (missing fields)
  - fields with ambiguous semantics
  - missing or inconsistent reason_code
  - subtle backward-compatibility smell
Possible examples:
- incomplete error responses;
- fields with ambiguous semantics;
- missing or inconsistent reason_code;
- one endpoint contract diverges from actual runtime behavior;
- inconsistent use of headers;
- subtle backward-compatibility smell.

D. Idempotency / retry / observability flaws:
  - retry causes a side effect before deduplication
  - structured logs miss one crucial field
  - reject cause is hard to reconstruct quickly
Possible examples:
- idempotency check happens too late;
- retry causes a side effect before deduplication;
- correlation-id disappears on one downstream call;
- structured logs miss one crucial field;
- reject cause is hard to reconstruct quickly.

E. Architectural flaws:
  - gateway knows too much about business rules
  - payment-service knows too much about decision rules
  - decision-hub partially loses ownership
  - shared module leaks business constants
Possible examples:
- service boundaries are blurred;
- gateway knows too much;
- payment-service knows too much about decision rules;
- decision-hub partially loses ownership;
- a mini-ESB smell appears through orchestration glue;
- shared module starts leaking business constants or business decisions.

═══════════════════════════════════════════════════════════════════════
PART 7 — BACKEND QUESTIONS TO PREPARE
═══════════════════════════════════════════════════════════════════════

Prepare a focused question bank that matches ONLY this repository.
Do NOT include generic Python theory or unrelated algorithms.
Use the following catalog as your canonical flaw library.
1. Duplicated decision logic in two services
2. Non-obvious idempotency
3. Lost correlation-id in one transition
4. Scattered / implicit status machine
5. Incomplete error model
6. Divergence between OpenAPI and runtime
7. APPROVE decision with failed posting / partial failure
8. Reject logic without explainability
9. Gateway knows too much
10. Audit ownership is split incorrectly
11. Hidden async smell
12. Decision data and transfer data diverge
13. Incorrect fallback policy when decision-hub is unavailable
14. Rule precedence is not transparent
15. Senior+ architectural degradation: mini-ESB / shared business leakage

For each flaw, always describe:
- changed files,
- symptom,
- root cause,
- expected analyst observation,
- recommended correction direction.


ALLOWED topics (only if genuinely present in this codebase):

Python basics (repository-relevant only):
- functions, arguments, return values
- if/else, boolean expressions
- exceptions and error handling
- modules and packages
- classes and methods
- decorators (only if present in middleware/logging/tracing)
- debugging and stack trace reading

Algorithms (only those that map to runtime logic):
- hash-table / dictionary thinking → idempotency key lookup
- set / uniqueness thinking → deduplication
- complexity thinking → scanning rules, evaluating decisions
- sorting / precedence → rule priority order

API/backend topics:
- REST resources and methods
- headers (X-Correlation-Id, Idempotency-Key)
- status codes and error model
- OpenAPI vs runtime implementation
- observability of distributed request flow
- contract-first behavior

SYSTEM ANALYSIS SKILL MAPPING:
Every question must map to one of these 6 layers:
  Layer 1: processing logic
  Layer 2: data/state
  Layer 3: API/integration
  Layer 4: middleware/retry/idempotency/observability
  Layer 5: incidents/RCA
  Layer 6: architecture

Questions must be grouped by:
  1. Code reading
  2. Business logic
  3. Data/state
  4. API/contracts
  5. Idempotency/retry
  6. Observability/RCA
  7. Architecture
  8. Senior deep-dive

Each question: directly grounded in this repository, supports 1:1 grading format, no generic trivia.


You must also prepare backend-oriented questions that fit this exact project.

IMPORTANT:
Do NOT dump generic backend theory.
Do NOT include everything from Python / algorithms / backend courses.
Select only topics that naturally match Decision Hub / sa-lab-training.

The allowed source domains are:

A. Python basics relevant to this project
Use only topics that help read and reason about this repository, such as:
- functions,
- arguments,
- return values,
- if / else,
- boolean expressions,
- exceptions,
- modules/packages,
- classes and methods,
- decorators only if relevant to middleware / tracing / logging,
- context managers only if genuinely present,
- typing only if present and useful,
- debugging / stack trace reading.

B. Algorithms and data structures relevant to this project
Use only topics that genuinely map to runtime logic, for example:
- hash-table / dictionary thinking for idempotency-key lookup,
- set / uniqueness thinking for deduplication,
- queue / ordering thinking only if relevant,
- complexity thinking for scanning rules and evaluating decisions,
- sorting / precedence only if relevant to rule order,
- data structure choice for audit / state reconstruction.
Do NOT introduce unrelated algorithm trivia.

C. API/backend topics relevant to this project
Use only:
- REST resources and methods,
- headers,
- status codes,
- error model,
- OpenAPI vs implementation,
- OAuth is NOT the focus here unless it exists in this repository,
- observability of distributed request flow,
- contract-first behavior.

D. System analysis skill mapping
Every selected backend question must map to one of the engineering layers:
1. processing logic
2. data/state
3. API/integration
4. middleware/retry/idempotency/observability
5. incidents/RCA
6. architecture

═══════════════════════════════════════════════════════════════════════

PART 8 — FILES TO CREATE
═══════════════════════════════════════════════════════════════════════

This repository should be senior-oriented by default.

Do not create separate beginner or middle versions in this run.
Instead:
- implement a senior-level training case in one repository,
- but ensure questions can later be asked with different depth depending on candidate level.

So the codebase must support:
- shallow reading for weaker candidates,
- deep reasoning for senior candidates.


You must prepare two different documentation layers:

----------------------------------
1. Candidate-facing material
----------------------------------
This material WILL stay visible in the repository.

Create / update:
- README.md

README.md must:
- describe the candidate case,
- explain the business context briefly,
- explain that this is a realistic banking sandbox,
- describe available services at a high level,
- include grading tasks/questions for the candidate,
- include reverse-engineering tasks,
- include backend-oriented questions relevant to the repository,
- avoid giving away the actual hidden flaws explicitly,
- avoid revealing answers.

The README must include sections like:
- Case Overview
- Business Context
- Services in Scope
- What the candidate should analyze
- Standard tasks
- Questions on code reading
- Questions on API/contracts
- Questions on idempotency / lifecycle / observability
- Architecture discussion prompts
- Optional deep-dive questions


Generate a focused bank of questions that match this repository.

Questions must be grouped by:

1. Code reading
2. Business logic
3. Data/state
4. API/contracts
5. Idempotency/retry
6. Observability/RCA
7. Architecture
8. Senior deep-dive

Each question must:
- be directly grounded in this repository,
- point to realistic investigation areas,
- avoid generic trivia,
- support one-to-one grading workshop format.

For backend questions, include only those that map naturally to:
- Python flow control,
- functions and method boundaries,
- exception handling,
- dictionary/hash-map style lookup for idempotency,
- state transitions,
- contract mismatch detection,
- log tracing,
- ownership and coupling.


----------------------------------
2. Facilitator-only material
----------------------------------
This material is ONLY for the grading organizer.

Create a separate hidden file, for example:
- .facilitator-notes.md
or
- .training-facilitator-notes.md

This file must be excluded from GitHub visibility via .gitignore if needed.

It must include, for every implemented flaw:
- flaw name,
- changed files,
- exact implementation summary,
- anti-pattern created,
- what analyst skill it tests,
- how to discover it,
- expected findings,
- expected correction direction,
- suggested probing questions,
- recommended depth for weaker vs stronger candidates.

Also create, if useful:
- .training-change-log.md

This hidden file should summarize all repository degradations and why they exist.

CANDIDATE-FACING (visible in repo):

  README.md — must include:
    - Case Overview (business context, realistic banking sandbox)
    - Services in Scope (4 services, high-level description only)
    - What the candidate should analyze
    - Standard tasks:
        * identify service ownership
        * reconstruct transfer lifecycle / status machine
        * identify where business decisions are taken
        * compare expected TO-BE flow vs actual degraded implementation
        * inspect idempotency behavior
        * inspect correlation-id propagation
        * identify mismatches between OpenAPI and runtime
        * propose documentation / ТЗ structure from code
        * propose fixes
    - Questions on code reading (no answers)
    - Questions on API/contracts
    - Questions on idempotency / lifecycle / observability
    - Architecture discussion prompts
    - Optional senior deep-dive questions

  Tone: serious, engineering-oriented, not gamified, not "toy challenge".
  Do NOT reveal actual flaws. Do NOT give answers.
  Frame as: "documentation is incomplete, infer behavior from code."


The candidate README should present the project as a reverse-engineering / system-analysis case.

Tone:
- serious,
- engineering-oriented,
- not gamified,
- not “toy challenge”.

It should frame the task like this:
- documentation is incomplete or outdated;
- candidate must infer behavior from code, structure, and contracts;
- candidate should restore proper understanding and documentation;
- candidate should identify architectural and analytical weaknesses.

The README should contain standard tasks such as:
- identify service ownership;
- reconstruct transfer lifecycle / status machine;
- identify where business decisions are taken;
- compare TO-BE flow and hidden AS-IS degradation;
- inspect idempotency behavior;
- inspect correlation-id propagation;
- identify mismatches between code and OpenAPI;
- propose documentation/TZ structure from code;
- propose fixes.


Generate a focused bank of questions that match this repository.

Questions must be grouped by:

1. Code reading
2. Business logic
3. Data/state
4. API/contracts
5. Idempotency/retry
6. Observability/RCA
7. Architecture
8. Senior deep-dive

Each question must:
- be directly grounded in this repository,
- point to realistic investigation areas,
- avoid generic trivia,
- support one-to-one grading workshop format.

For backend questions, include only those that map naturally to:
- Python flow control,
- functions and method boundaries,
- exception handling,
- dictionary/hash-map style lookup for idempotency,
- state transitions,
- contract mismatch detection,
- log tracing,
- ownership and coupling.



FACILITATOR-ONLY (hidden from candidate):

  .training-facilitator-notes.md — for every implemented flaw:
    - flaw name
    - changed files
    - exact implementation summary
    - anti-pattern created
    - analyst skill tested
    - how to discover (code / logs / API / DB)
    - expected candidate findings
    - expected correction direction
    - suggested probing questions
    - recommended depth: weaker vs stronger candidates

  .training-change-log.md — summary of all degradations and why they exist

  Add to .gitignore:
    .training-facilitator-notes.md
    .training-change-log.md

═══════════════════════════════════════════════════════════════════════
PART 9 — SAFETY CONSTRAINTS
═══════════════════════════════════════════════════════════════════════

Do not do full chaos.
Do not make the whole repository unusable.
Do not break every endpoint.
Do not delete core explanatory value of the original project.

The repository must remain:
- runnable if reasonably possible,
or at least
- statically analyzable,
- structurally coherent,
- pedagogically useful.

If a degradation risks making the project too broken, reduce it.


- The system must remain runnable (or at minimum statically analyzable)
- Do not break every endpoint simultaneously
- Do not delete the core explanatory value of the original project
- If a degradation risks making the project unanalyzable, reduce it
- One service must remain "clean" as a reference point for comparison
- The candidate must be able to detect flaws by reading, not by guessing

═══════════════════════════════════════════════════════════════════════
PART 10 — SENIOR SCOPE
═══════════════════════════════════════════════════════════════════════

Implement ONE senior-level repository (not separate beginner/middle versions).
The codebase must support:
- shallow reading for weaker candidates
- deep reasoning for senior candidates

Questions can be asked with different depth depending on candidate level.
The flaws must be diagnosable at different levels of detail.


═══════════════════════════════════════════════════════════════════════
FIRST TASK — START HERE
═══════════════════════════════════════════════════════════════════════

Start with ANALYSIS ONLY. Do NOT modify any code.

Follow this workflow strictly:

Step 1. Inspect repository
Step 2. Propose degradation plan
Step 3. Propose exact files to change
Step 4. Propose candidate README structure
Step 5. Propose facilitator hidden file structure
Step 6. Wait for approval
Step 7. Implement only approved flaws
Step 8. Update README
Step 9. Create hidden facilitator notes
Step 10. Summarize all changes

Do the following first:
1. Inspect current repository structure (list all files and services);
2. Propose senior-level degradation plan using the 5 flaws from Part 5 - - propose a senior-level degradation plan using the first 5 recommended flaws;

3. For each flaw: map to analyst skills + specify exact files to change - - map each flaw to analyst skills and grading objectives;
4. propose README.md structure for candidate-facing case;
5. Propose .training-facilitator-notes.md structure
6. Propose focused question bank (grouped by 8 categories from Part 7) - - propose a focused list of backend questions/topics that fit this repository and only this repository.


Show the complete plan. Then wait for approval before modifying anything.