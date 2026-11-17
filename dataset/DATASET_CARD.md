# Dataset card: taskforge-bench v1.0.0

66 executable bug-fix tasks across 6 small Python repositories, generated 2026-11-17 08:34 UTC
(seed 7, Python 3.13.18, pytest 9.1.1).

## What a record contains

| Field | Meaning |
|---|---|
| `instance_id` | Stable id, `tf-<repo>-<n>` |
| `problem_statement` | Developer-facing description built from observable failures only |
| `snapshot` | Full buggy repo (source and tests) as `{path: text}` |
| `patch` | Golden unified diff (source files only) |
| `fail_to_pass` | Tests that fail on the snapshot and pass after the golden patch |
| `pass_to_pass` | Tests that must keep passing (regression guard) |
| `bug_count` / `mutation_kinds` | 1 or 2 injected bugs and their categories |
| `difficulty` | Tier plus the reference solver's attempts (see below) |
| `quality`, `validation` | Checks every task passed |

## How tasks are made and checked

1. Every single-token mutation of each clean repo is injected and run against the suite.
2. Bugs the tests cannot see, that hang, or that break most of the suite are rejected.
3. Survivors are de-duplicated by failing-test signature and sampled across mutation kinds.
   Some are combined into two-bug tasks (different functions, so both fixes are required).
4. Each candidate is re-run to rule out flakiness, the golden patch is applied with a
   context-verifying patcher, and the full suite must go green with the exact original test set.
5. The problem statement must not contain any changed line of the patch.
6. A reference solver (spectrum-based fault localization with Ochiai scores over per-test line
   coverage, then greedy single-token repair) gives a difficulty tier from the number of edit
   trials it needs: easy <= 3, medium <= 10, otherwise hard (including unsolved within budget).

`python -m taskforge verify dataset/tasks.jsonl` re-checks all of this from the JSONL alone.

## Funnel

| Stage | Count |
|---|---|
| Candidate bugs injected | 480 |
| Rejected: tests do not notice (equivalent or untested) | 38 |
| Rejected: infinite loop / timeout | 14 |
| Rejected: crashes test collection | 0 |
| Rejected: breaks most of the suite | 16 |
| Usable single + two-bug candidates | 589 |
| Dropped: same failing-test signature as another task | 200 |
| Dropped: over the per-repo quota | 323 |
| Rejected: unstable across re-runs | 0 |
| Rejected: patch did not round-trip | 0 |
| Rejected: golden patch left tests failing | 0 |
| Rejected: issue text leaked the fix | 0 |
| Accepted tasks | 66 |

## Repositories

`Mutation score` = share of injected bugs the repo's own tests detect.

| Repo | LOC | Tests | Mutants | Mutation score | Tasks |
|---|---|---|---|---|---|
| `calc` | 110 | 46 | 79 | 87% | 11 |
| `datekit` | 84 | 82 | 168 | 91% | 11 |
| `graphkit` | 113 | 36 | 43 | 93% | 11 |
| `intervals` | 97 | 57 | 67 | 91% | 11 |
| `lrucache` | 88 | 26 | 32 | 94% | 11 |
| `textkit` | 125 | 53 | 91 | 98% | 11 |

## Distributions

- Difficulty: easy: 31, hard: 20, medium: 15
- Mutation kinds: arithmetic_operator: 16, augmented_assignment: 11, boolean_constant: 11, boolean_logic: 7, comparison_boundary: 9, comparison_negation: 8, min_max_swap: 2, off_by_one: 17
- Mean fail-to-pass tests per task: 8.0; mean pass-to-pass: 42.0
- Reference solver solved 74% of tasks; 2% of tasks admit a valid fix that differs from the golden patch.

## Limitations

- Bugs are synthetic single-token mutations, not mined from real commit history.
- The reference solver shares the generator's edit catalogue, so tiers are a calibrated
  proxy for difficulty, not a measure of how a language model would perform.
- Problem statements are generated from test output; they are accurate but terse.
- Sandboxing is process-level (temp dir, timeout, rlimits), not a security boundary.
