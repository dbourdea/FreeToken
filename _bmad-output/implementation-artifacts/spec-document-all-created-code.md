---
title: 'Document every branch-created code line'
type: 'chore'
created: '2026-09-15'
status: 'done'
route: 'full'
review_loop_iteration: 3
baseline_commit: 'a5846c0847cb371313b9ad7ceb93a1933a48d967'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The `feat/freetoken-swap` implementation contains substantial code whose individual lines do not all explain both their operation and their purpose. The user requires all code created to date, and all future code, to carry those explanations.

**Approach:** Use merge base `9ef3651309fe4058672f2cc92069238dea06be1b` as the ownership boundary. Add an adjacent, meaningful native-language comment for every nonblank executable or configuration line introduced after that base, explaining what the line does and why it exists, without changing runtime behavior.

## Boundaries & Constraints

**Always:** Cover branch-created Python runtime, benchmark, test, embedded HTML/CSS/JavaScript, workflow YAML, example YAML/TOML, and `pyproject.toml` additions. Preserve shebang placement, module docstrings, decorators, multiline grammar, exact protocol fixtures, exception text, serialized bytes, and public behavior. Explain syntax-only delimiters at their nearest valid structural boundary. Comments themselves do not require recursive comments. Retain the draft PR and private-artifact policy.

**Never:** Modify the pinned llama-swap checkout, protected runtime/service/model/GPU state, upstream-owned pre-base logic, generated `_bmad/` files, or prose-only documentation merely to inflate coverage. Do not merge PRs, activate services, publish raw artifacts, or substitute generic comments that fail to identify both action and rationale.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Python statement | Branch-added executable line | Adjacent `#` comment states action and purpose | Compilation/tests catch grammar or behavior changes |
| Embedded web code | HTML/CSS/JavaScript inside Python literal | Native embedded comment documents each safe line | Exact payload/string fixtures remain byte-identical when comments would alter semantics |
| YAML/TOML/config | Branch-added nonblank setting or command | Adjacent format-valid comment explains value and reason | Parser/workflow validation catches invalid syntax |
| Grammar-sensitive content | Docstring, multiline literal, backslash continuation, decorator, or fixture bytes | Explain at nearest valid boundary without mutating value or attachment | Preserve original content and document exception structurally |

</frozen-after-approval>

## Code Map

- `.github/workflows/freetoken-swap-daemon.yml`, `examples/freetoken-swap.{toml,yaml}`, `pyproject.toml` -- branch-created operational configuration requiring native comments.
- `benchmarks/swap/*.py` -- three opt-in qualification harnesses; preserve fail-closed maintenance gates and private artifacts.
- `python/freetoken/daemon/{activity,app,catalog,client,inference_proxy,metrics,osproc,performance,proxy,readiness,router,serve_manager,server}.py` and `python/freetoken/server/control_api.py` -- production delta, including embedded router UI.
- `tests/daemon/*.py` -- branch-created behavioral and qualification coverage; preserve exact assertions and fixtures.
- `docs/*.md`, `README.md`, `python/freetoken/daemon/README.md` -- prose evidence, not executable code; do not mechanically annotate.

## Comment Quality Contract

- Every explanation must be specific to the documented line and its immediate enclosing symbol. The `what` clause names the semantic effect, not merely the token or delimiter; the `why` clause names the concrete consumer, invariant, failure path, or state transition that requires it.
- Imports must name at least one actual consumer or operation that needs the imported symbol. Runtime lines must connect to their concrete lifecycle/API/data-flow role. Reusing one module-wide rationale across unrelated lines is prohibited.
- Structural delimiters must identify the call, collection, signature, or branch they complete and why that construct must remain grouped. Do not emit generic “close expression,” “invoke with supplied arguments,” “set from,” or equivalent templates without the concrete semantic role.
- Never truncate a comment with `...`, embed historical physical line numbers, or copy secrets/private deployment values. Exact literals and block scalars are described at a stable enclosing boundary without changing their bytes.
- Tests must identify whether a line arranges a condition, performs the behavior, or asserts the outcome, plus the regression/failure mode it protects. Workflow keys must explain their individual operational choice. Example numeric/boolean values must be labeled illustrative and explain their tradeoff rather than imply universal suitability.
- Review every generated explanation against the underlying symbol/caller before accepting coverage. Form/count checks alone are insufficient.
- Never use textual-neighbor clauses such as “between X and Y,” the placeholders “declared structural boundary” or “literal fixture value,” or hedged consumers such as “parser, serializer, or API consumer.” Keep each generated explanation at or below 320 characters so imports and dense expressions remain reviewable.
- Describe `raise` as propagating a failure, `try` as establishing a handler boundary, and `except` as the actual handling behavior. Name the concrete behavior of route, middleware, property, classmethod, dataclass, and lifecycle decorators rather than collapsing them into one decorator template.
- Distinguish runtime accumulators from test fixtures, and distinguish GitHub workflow/JUnit concepts from model-router, llama-swap, and `ft serve` configuration. Test assertions must state the expected behavior or regression, not “assert the assert” or “exact condition.”
- Assertion rationales must describe failure when the asserted predicate is false. Side-effect calls such as `sleep`, `extend`, mutation, notification, and cleanup must not claim their `None` return is consumed. New exception construction is described as raising or signaling, not propagating an existing exception.
- Assignments and returns must name the concrete invariant, normalized value, state transition, or caller contract where it is available; tokenized expressions plus “later consumed” are insufficient. TOML table headers establish namespaces, and each example setting must explain its own operational tradeoff.
- Do not clip string or argument text to an unterminated fragment. Embedded reporter comments must explain aggregation, escaping, annotation, or failure-gating roles at stable scalar boundaries.

## Tasks & Acceptance

**Execution:**
- [x] Inventory added hunks from the pinned merge base and produce a deterministic coverage list by file and language.
- [x] Build symbol- and usage-aware explanations satisfying the Comment Quality Contract for every eligible Python and embedded web-code line while preserving grammar and exact-value fixtures.
- [x] Add key/value-specific explanations satisfying the Comment Quality Contract for every eligible workflow/configuration line using YAML or TOML syntax.
- [x] Review the complete diff for generic/repeated filler, factual errors, truncation, stale line references, accidental executable changes, secrets/private metadata, and untouched upstream code.
- [x] Measure and record source-size/import-parse impact, run deterministic verification, and prepare only the intended documentation delta for review; commit, push, and exact-head GitHub verification follow the mandatory review step.

**Acceptance Criteria:**
- Given the merge-base diff, when every introduced executable/configuration line is inspected, then it has an adjacent meaningful explanation of both what it does and why, or is covered at the nearest valid boundary because inline insertion would change grammar or exact data.
- Given the pre-comment commit and final commit, when executable behavior and public outputs are compared through the existing suite, then all daemon tests pass with no logic regression.
- Given the final implementation state, when pre-publication review begins, then exactly the intended product files and this spec are staged, generated `_bmad/` runtime files are excluded, and commit/push/exact-head GitHub verification remain explicit post-review deliverables.

## Implementation Notes

- The pinned merge-base inventory found 11,714 eligible nonblank code/configuration lines across 31 tracked files; the transformation reported 11,714 covered lines.
- Python comments use tokenizer/AST context to distinguish definitions, calls, assignments, parameter defaults, keyword arguments, control flow, literals, and structural continuations. Multiline strings and explicit backslash continuations are documented at their nearest safe boundary.
- YAML block-scalar payloads remain byte-for-byte unchanged; one boundary comment per owned payload line is placed before the scalar key. TOML/YAML comments otherwise sit adjacent to their settings.
- A one-use refinement helper was created during implementation and deleted before review; it is not part of the repository diff.
- Final local evidence: Python compilation passed; stripping only the new comments reproduced the exact baseline bytes for all 31 product files; Python ASTs for 27 edited files remained identical; all four YAML/TOML files parsed; `tests/daemon` completed with 345 passed and 7 expected platform skips; `git diff --check` passed; prose-only documentation remained unchanged; and the privacy-pattern scan found no candidate secrets.
- The fail-closed coverage audit found exactly 11,714 valid what/why comments for 11,714 eligible branch-created lines. It found no missing coverage, non-comment byte differences, malformed explanations, truncated expressions, physical multiline line references, or rejected generic phrases.
- After loop-2 shortening, the 31 product files increased from 680,262 bytes to 3,137,738 bytes (2,457,476 bytes; 4.613x). A fresh five-run median parse of all 27 Python files increased from 337.129 ms to 459.453 ms (1.363x) on this host; this local microbenchmark does not claim runtime request-path overhead.
- Loop-2 final evidence: all 11,714 explanations are 320 characters or fewer; prior rejected phrases and placeholders have zero hits; the cited workflow, routing-group, API-key, readiness, malformed-path, runtime-accumulator, and test-action errors were corrected; exact non-comment bytes and Python ASTs still match baseline; compilation, TOML/YAML parsing, and `git diff --check` pass; and `tests/daemon` again reports 345 passed and 7 platform skips.
- Loop-3 final evidence: exact 11,714-line coverage and 320-character maximum remain intact; assertion truth, side-effect calls, pass handling, keyword-only syntax, exception origin, TOML namespaces/settings, clipped qualifier options, and reporter boundaries were corrected; non-comment bytes and ASTs still match baseline; compilation and `git diff --check` pass; and `tests/daemon` again reports 345 passed and 7 skips.
- Post-review patch evidence: the final cited sentinel, signal, readiness-loop, checkpoint, dependency-continuation, JUnit fallback, and `None`-assertion defects were corrected. The final invariant audit again reports 31 files, 11,714 comments, a 320-character maximum, zero non-comment/AST mismatches, valid TOML/YAML, and a clean `git diff --check`; the latest full suite remains 345 passed and 7 skipped.
- Commit, push, and exact-head hosted CI verification remain pending until the mandatory review workflow permits remote operations.

## Spec Change Log

- 2026-09-15 review loop 1 — Trigger: independent reviewers found the first derivation counted comments but allowed syntax restatement, repeated module-wide rationales, factual errors, truncated expressions, stale physical-line references, weak workflow/example/test explanations, and unacknowledged source bloat. Amendment: added the Comment Quality Contract, reset affected tasks, and required symbol/usage-aware generation, factual review, and cost measurement. Known-bad state avoided: 11,714 formally present but predominantly template-generated comments that reduce readability or misdescribe behavior. KEEP: pinned merge-base ownership; exact one-for-one eligible-line inventory; unchanged multiline literal/YAML scalar bytes; no protected-runtime access; AST/config semantic equivalence; privacy scan; full daemon suite; generated `_bmad/` exclusion.
- 2026-09-15 review loop 2 — Trigger: independent review found remaining systemic cross-domain templates, reversed exception-flow descriptions, vague decorator/literal/assertion explanations, unstable neighbor clauses, and individual comments up to 1,791 characters. Amendment: prohibited the observed placeholders and neighbor clauses, capped explanation length, required concrete exception/decorator/test semantics, and required strict workflow/router/fixture domain separation. Known-bad state avoided: formally complete coverage that still misleads maintainers about failure propagation, GitHub reporting, model routing, and expected test outcomes. KEEP: all loop-1 constraints; exact 11,714-line coverage; zero executable/config byte changes after comment stripping; 345-pass/7-skip suite; exact literals and block scalars; measured 5.308x source-size and 1.117x parse-time ratios.
- 2026-09-15 review loop 3 — Trigger: review found assertions with inverted truth semantics, side-effect calls documented as consumed return values, generic assignment/return rationales, TOML tables mislabeled as arguments, repeated unrelated example-setting rationales, and clipped argument text. Amendment: added explicit truth, side-effect, exception-origin, assignment/return, table/value, clipping, and embedded-reporter rules. Known-bad state avoided: comments that pass phrase scans while inventing data flow or hiding safety/configuration intent. KEEP: all prior constraints and verified coverage/byte-equivalence/test evidence; corrected workflow gate, readiness, API-key, routing-group, malformed-path, and runtime-accumulator explanations; 320-character limit.

## Review Triage Log

- Blind-1 — `medium`, `bad_spec`: verified syntax-only comments such as `app.py` delimiter explanations do not state the construct's semantic role; grouped into systemic comment-quality re-derivation.
- Blind-2 — `medium`, `bad_spec`: verified imports reuse a generic app-wide rationale instead of naming actual consumers; grouped into systemic comment-quality re-derivation.
- Blind-3 — `medium`, `bad_spec`: verified `/ready` comments incorrectly describe stop/accounting controls, risking maintainer misunderstanding of supervisor readiness; grouped into systemic comment-quality re-derivation.
- Blind-4 — `medium`, `bad_spec`: verified `fresh_health` comments incorrectly mention streaming cleanup rather than bypassing prior-generation cache; grouped into systemic comment-quality re-derivation.
- Blind-5 — `medium`, `bad_spec`: verified 28 comments truncate decisive expression text with `...`; grouped into systemic comment-quality re-derivation.
- Blind-6 — `medium`, `bad_spec`: verified workflow comments repeat a lane-wide rationale and omit the repository gate, timeout, pinned action, and result-reporting reasons; grouped into systemic comment-quality re-derivation.
- Blind-7 — `medium`, `bad_spec`: verified YAML scalar boundary comments embed physical line numbers that become stale after edits; grouped into systemic comment-quality re-derivation.
- Blind-8 — `medium`, `bad_spec`: verified example settings repeat “safe configuration” without explaining illustrative values/tradeoffs; grouped into systemic comment-quality re-derivation.
- Blind-9 — `medium`, `bad_spec`: verified test comments repeat “remains enforced” without arrange/act/assert role or protected failure mode; grouped into systemic comment-quality re-derivation.
- Blind-10 — `false`, `reject`: the user instructed this assistant to comment future code but did not request a repository linter or CI policy; absence of enforcement code is not a defect in this change.
- Blind-11 — `false`, `reject`: workflow parsed values were byte/structure-equivalent to baseline and exact-head hosted CI remains a publication gate, so a new `actionlint` dependency is not needed to validate comment-only edits.
- Blind-12 — `false`, `reject`: embedded HTML/CSS/JavaScript literal bytes were unchanged and Python AST constant equality proved that fact, so browser-side validation is not required for this comment-only boundary documentation.
- Blind-13 — `false`, `reject`: verification commands, baseline commit, counts, and expected results are recorded and independently reproducible; committing raw transient logs was neither requested nor safe/necessary.
- Blind-14 — `medium`, `bad_spec`: verified the 2.6 MB source expansion has developer/import/distribution costs that were not measured or acknowledged; retained as a separate measurement requirement in re-derivation.
- Blind-15 — `high`, `bad_spec`: verified predominant generated templates conflict directly with the approved semantic-comment example and falsely satisfy checked acceptance boxes; grouped into systemic comment-quality re-derivation.
- Edge-1 — `medium`, `bad_spec`: verified the workflow-name explanation repeats the global CI rationale rather than why the display name identifies this lane; duplicate root cause retained as its own verdict row, then grouped with systemic quality findings.
- Edge-2 — `false`, `reject`: `AM` is expected because Step 4 requires changing status to `in-review` without staging; the final status will be staged before commit, so reviewed and committed specs will not diverge.
- Verification-gap — no findings reported.
- Loop2-Blind-1 — `false`, `reject`: `git diff --check` passed against the worktree; CRLF bytes existed only in the temporary review-diff serialization and are not trailing whitespace in product files.
- Loop2-Blind-2 — `false`, `reject`: replacing per-line documentation with only selective comments would violate the human-owned frozen intent requiring every branch-created code/configuration line to be explained.
- Loop2-Blind-3 — `false`, `reject`: the comments adjacent to multiline docstrings describe the underlying string fragments that Python exposes through introspection; they do not claim the `#` comment itself is part of `__doc__`. The separate “declared structural boundary” wording defect is accepted below.
- Loop2-Blind-4 — `medium`, `bad_spec`: verified `.github/workflows/freetoken-swap-daemon.yml` attributes repository gating to `if: always()` instead of its real purpose of preserving result reporting after prior outcomes.
- Loop2-Blind-5 — `medium`, `bad_spec`: verified the workflow attributes `PYTHONPATH` to the JUnit reporter rather than pytest imports in the daemon-test step.
- Loop2-Blind-6 — `medium`, `bad_spec`: verified both TOML `group = "interactive"` explanations incorrectly describe GitHub ref concurrency instead of shared model routing/exclusivity policy.
- Loop2-Blind-7 — `medium`, `bad_spec`: verified example YAML model commands incorrectly use JUnit-reporter rationales for `ft serve` arguments.
- Loop2-Blind-8 — `medium`, `bad_spec`: verified `wait_for_ready` describes `while True` as candidate iteration rather than bounded readiness polling with explicit terminal conditions.
- Loop2-Blind-9 — `medium`, `bad_spec`: verified `wait_for_ready` describes `sleep()` as feeding a return rather than pacing injectable polling.
- Loop2-Blind-10 — `medium`, `bad_spec`: verified the `wait_for_ready` return annotation explanation does not identify the heterogeneous readiness-result mapping contract.
- Loop2-Blind-11 — `medium`, `bad_spec`: verified the `/ready` return explanation omits the supervisor-facing 200/503 acceptance contract.
- Loop2-Blind-12 — `medium`, `bad_spec`: verified runtime accumulator `parts = []` is mislabeled as a fixture.
- Loop2-Blind-13 — `medium`, `bad_spec`: verified the canary `model` field uses a hedged generic consumer rather than its concrete routed-model selection role.
- Loop2-Blind-14 — `medium`, `bad_spec`: verified test assertions use circular tokenized prose and omit the expected behavior or regression they protect.
- Loop2-Blind-15 — `medium`, `bad_spec`: verified the spec's checked semantic-review task and no-defect audit claim were contradicted by current examples; tasks were reset for re-derivation.
- Loop2-Blind-16 — `low`, `patch`: the verification command retained an unresolved `<pre-comment-head>` placeholder; replace it with baseline commit `a5846c0847cb371313b9ad7ceb93a1933a48d967` before completion.
- Loop2-Blind-17 — `low`, `reject`: source and parse costs are measured explicitly, while editor/indexer, formatter, merge-conflict, and distribution effects lack a deterministic repository check and do not change the user-mandated per-line scope.
- Loop2-Edge-1 — `medium`, `bad_spec`: verified `app.py` documents malformed percent-escape rejection (`return None`) as a literal fixture return.
- Loop2-Edge-2 — `medium`, `bad_spec`: verified workflow JUnit aggregation lines retain placeholder structural explanations rather than tests/failures/errors summation semantics.
- Loop2-Edge-3 — `medium`, `bad_spec`: carried Loop2-Blind-4; the `if: always()` rationale is factually wrong at the same location.
- Loop2-Edge-4 — `medium`, `bad_spec`: verified example TOML `api_keys` discusses model memory/startup tradeoffs rather than router authentication and credential replacement.
- Loop2-Edge-5 — `false`, `reject`: carried Edge-2; Step 4 explicitly prohibits staging while constructing and reviewing the diff, so an empty index and untracked in-review spec are expected until review succeeds.
- Loop2-Extra-1 — `medium`, `bad_spec`: verified `test_catalog.py` misclassifies the `wait_for_ready(...)` action assignment as function-signature binding.
- Loop2-Extra-2 — `medium`, `bad_spec`: verified hundreds of “declared structural boundary” explanations fail to name the expression or collection being completed.
- Loop2-Extra-3 — `medium`, `bad_spec`: verified generic `raise`, `try`, and decorator templates reverse or obscure concrete control flow and registration behavior.
- Loop2-Extra-4 — `medium`, `bad_spec`: verified comments up to 1,791 characters and 1,009 textual-neighbor clauses are unstable and make dense imports unreadable; a 320-character limit and neighbor-clause prohibition were added.
- Loop2-Verification-1 — `medium`, `bad_spec`: carried Loop2-Blind-4; independent verification-gap review confirmed the same false `if: always()` rationale and reported no additional gaps.
- Loop3-Blind-1 — `medium`, `bad_spec`: verified assertion comments described failure when a true predicate “violates” an invariant; rationales now require the predicate to remain true and identify false as the failure state.
- Loop3-Blind-2 — `medium`, `bad_spec`: verified `time.sleep(1)` was documented as supplying a later exception; it now explicitly paces bounded health polling.
- Loop3-Blind-3 — `medium`, `bad_spec`: verified `raw.extend()` was documented as a consumed return value; it now describes mutation of the accumulated stream buffer.
- Loop3-Blind-4 — `medium`, `bad_spec`: verified `pass` was mislabeled as predicate evaluation; pass lines now document suppression of the anticipated handled exception.
- Loop3-Blind-5 — `medium`, `bad_spec`: verified the bare signature `*` was mislabeled as a predicate fragment; it now documents the keyword-only API constraint.
- Loop3-Blind-6 — `medium`, `bad_spec`: verified three function definitions used “execute def” boilerplate; definitions now describe declaration and caller reuse, with the hostname helper's safety contract retained in its adjacent docstring.
- Loop3-Blind-7 — `low`, `bad_spec`: verified newly constructed errors were called propagated exceptions; generated wording now says they are raised for the caller.
- Loop3-Blind-8 — `medium`, `bad_spec`: verified broad assignment templates often omitted the reason for normalization or state production; the strengthened contract now requires the concrete invariant where available.
- Loop3-Blind-9 — `medium`, `bad_spec`: verified broad return templates only said callers depend on results; the strengthened contract now requires the caller guarantee where available.
- Loop3-Blind-10 — `medium`, `bad_spec`: verified unrelated TOML settings shared one model/memory/port rationale; each example key now has a setting-specific operational tradeoff.
- Loop3-Blind-11 — `medium`, `bad_spec`: verified TOML table headers were mislabeled as command arguments; they now describe the namespace each table opens.
- Loop3-Blind-12 — `medium`, `bad_spec`: verified three qualifier comments clipped option/help or encoding text into unterminated fragments; those lines now document the complete option or artifact-write behavior.
- Loop3-Blind-13 — `medium`, `bad_spec`: verified embedded reporter delimiter comments did not explain their aggregation and diagnostic roles; cited boundaries now name count aggregation, summary formatting, case filtering, and detail selection.
- Loop3-Blind-14 — `false`, `reject`: carried Loop2-Blind-3; comments outside multiline strings describe the underlying docstring fragments without altering the introspected string bytes.
- Loop3-Blind-15 — `medium`, `bad_spec`: verified checked completion claims were premature while the above factual defects remained; tasks were reset during correction and require another independent review.
- Loop3-Edge-1 — `medium`, `bad_spec`: carried Loop3-Blind-2; the sleep data-flow claim was false and was corrected.
- Loop3-Edge-2 — `medium`, `bad_spec`: carried Loop3-Blind-2; the same line invented consumption of a `None` return.
- Loop3-Edge-3 — `medium`, `bad_spec`: carried Loop3-Blind-11; `[router]` opens a TOML table rather than representing a command argument.
- Loop3-Edge-4 — `medium`, `bad_spec`: carried Loop3-Blind-15; the clean-review claim was premature while the sleep defect remained.
- Loop3-Edge-5 — `false`, `reject`: carried Edge-2 and Loop2-Edge-5; the review workflow prohibits staging until independent review succeeds.
- Loop3-Verification — no verification gaps reported.
- Loop4-Blind-1 — `medium`, `patch`: verified the llama-swap validation comment remained clipped; directly replaced it with the complete pre-launch validation purpose.
- Loop4-Blind-2 — `false`, `reject`: carried Loop2-Blind-3 and Loop3-Blind-14; adjacent comments describe underlying docstring fragments without claiming comments are part of `__doc__`.
- Loop4-Blind-3 — `medium`, `patch`: verified two `None` capture assertions were mislabeled as delimiters; directly replaced them with eviction and retention semantics.
- Loop4-Blind-4 — `medium`, `patch`: verified the signal handler described a newly raised `KeyboardInterrupt` as propagated; directly documented signal-to-interruption conversion.
- Loop4-Blind-5 — `medium`, `patch`: verified SIGTERM registration was explained through the neighboring SIGHUP call; directly documented its restoration-path purpose.
- Loop4-Blind-6 — `medium`, `patch`: verified `MAX_JOBS` was tied to config validation instead of native-extension compilation; directly documented the two-job build cap.
- Loop4-Blind-7 — `medium`, `patch`: verified `proc = None` was mislabeled as fixture state; directly documented the conditional-cleanup sentinel.
- Loop4-Blind-8 — `medium`, `patch`: verified `config +=` omitted the generated model stanza role; directly documented command, readiness, proxy, and optional-TTL sequencing.
- Loop4-Blind-9 — `medium`, `patch`: verified the main `while True` omitted its readiness terminal conditions; directly documented listing success, process exit, and deadline expiry.
- Loop4-Blind-10 — `medium`, `patch`: verified `break` was mislabeled as predicate structure; directly documented successful readiness-loop exit.
- Loop4-Blind-11 — `medium`, `patch`: verified the half-second sleep was tied to a later trial loop; directly documented readiness retry backoff.
- Loop4-Blind-12 — `medium`, `patch`: verified three `save()` calls inherited unrelated neighboring expressions; directly documented trial, cancellation, and restoration checkpoints.
- Loop4-Blind-13 — `medium`, `patch`: verified pip continuation lines were called separate commands; directly documented each constraint as part of the shared install command.
- Loop4-Blind-14 — `medium`, `patch`: verified clean-review evidence was premature for the cited lines; this patch and post-patch verification supersede that claim.
- Loop4-Edge-1 — `medium`, `patch`: verified `observed = None` was mislabeled as fixture state; directly documented the not-yet-fetched statistics sentinel.
- Loop4-Edge-2 — `medium`, `patch`: verified reporter fallback was described as terminal handling; directly documented failure-node to error-node fallback.
- Loop4-Edge-3 — `medium`, `patch`: verified the hostname return contract remained generic; directly documented that the returned identity passed the exact-host safety gate.
- Loop4-Edge-4 — `false`, `reject`: carried Edge-2, Loop2-Edge-5, and Loop3-Edge-5; staging is intentionally prohibited until this review and patch verification finish.
- Loop4-Verification — no verification gaps reported.

## Design Notes

Comments should name concrete roles rather than restating syntax. For example, prefer “Normalize the requested alias so all lifecycle locks share one canonical identity” over “Assign the canonical variable.” A structural closing line may be explained by the comment attached to the construct it closes.

## Verification

**Commands:**
- `python -m compileall -q python/freetoken/daemon python/freetoken/server benchmarks/swap tests/daemon` -- expected: all edited Python parses.
- `python -m pytest tests/daemon -q` -- expected: complete local daemon suite passes with only platform-qualified skips.
- `git diff --check` -- expected: no whitespace or patch errors.
- `git diff --exit-code a5846c0847cb371313b9ad7ceb93a1933a48d967 -- docs README.md python/freetoken/daemon/README.md` -- expected: prose evidence remains unchanged.
- Public GitHub API check for the pushed exact head -- expected: `FreeToken swap daemon` completes successfully and PR #1 remains draft.
