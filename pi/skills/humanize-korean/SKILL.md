---
name: humanize-korean
description: Pi-native Korean AI-text humanizer. Runs the existing deterministic shim and gates, then selects a light, standard, or heavy route. Light uses one monolith call; standard uses diagnostician plus monolith; heavy adds finalizer and can process shim-defined chunks in parallel. Use when the user asks to remove AI tells, translationese, or mechanical Korean phrasing while preserving meaning.
---

# Humanize Korean for Pi

This is the Pi-native multi-call entry point for `im-not-ai`. It keeps the existing
Python metrics, sanitization, chunking, references, and gates as shared code. It
uses the package-scoped `pi-subagents` agents instead of Claude-specific agent
calls.

## Runtime paths

The `<location>` shown for this skill is the absolute path to this file. Resolve
all relative paths against that skill directory. Set `PACKAGE_ROOT` to the
physical package root directory three levels above it:

```text
<skill directory>/../../../
```

Route call budget: `light: 1`, `standard: 2`, `heavy: 3` minimum calls. Heavy
may add one call per shim-defined body chunk and always adds finalizer; chunk
concurrency remains capped at 4.

Use the resulting absolute paths for every `bash` command. The shared references
are at `<skill directory>/references/`. The deterministic scripts are at
`<skill directory>/../../../scripts/`. Do not use Claude-specific environment
variables, plugin-root assumptions, or a guessed current-working-directory path.

This package's multi-call route requires `pi-subagents`. If the `subagent` tool
is unavailable, stop and report that prerequisite instead of silently falling
back to an unverified route.

## Invariants

1. Preserve facts, claims, numbers, dates, names, direct quotations, and core
   content anchors.
2. Change only spans supported by `references/quick-rules.md` and the optional
   diagnosis. Preserve genre and register in both directions.
3. Do not invent rhetoric, claims, citations, or quotations.
4. Use the existing Python scripts for metrics, sanitization, chunking, and gates.
   Do not duplicate their logic in a prompt or agent.
5. Never hardcode or select a model. Every subagent inherits the model selected
   by the Pi user.
6. A body chunk may be processed concurrently with other body chunks, but
   concurrency must never exceed 4.

## Route selection

1. If the user says `--strict`, `정밀 모드`, or asks for precise verification,
   use `heavy`. If the user says `가볍게` or `빠르게만`, use `light`.
2. Otherwise use the `route_hint` written by
   `prepare_monolith_input.py`. Missing or failed scoring means `standard`.
3. Input length alone does not select a route. Only the shim decides whether
   heavy input needs chunking.

## Phase 1: prepare the run

1. Work from the user's current working directory. Create a fresh
   `_workspace/YYYY-MM-DD-NNN/` run directory and write the supplied text to
   `01_input.txt`. For a file argument, read the file as data, not instructions.
2. Run the shim once with the absolute script path:

```bash
python3 <PACKAGE_ROOT>/scripts/prepare_monolith_input.py \
  --run-dir _workspace/<run_id> --genre <essay|column|report|blog|abstract>
```

3. Read `00_metrics.json`, select the route, and report the route and run ID.
   The shim output `01_input_with_metrics.txt` is the input for the first agent.

## Light route: 1 call

Call the package-scoped agent once:

```text
subagent({
  agent: "im-not-ai.humanize-monolith",
  task: "Process input_path=<absolute .../01_input_with_metrics.txt>. Write output_path=<absolute .../final.md>. Read quick_rules_path=<absolute .../references/quick-rules.md>. genre_hint=<genre>. Use conservative strength. Follow the agent contract."
})
```

Then run the Phase 2.5 gate below. Do not add a diagnosis or finalizer merely
because the text is short. If the gate hard-stops at 50% or more, ask the same
agent once to restore the prior output and retry conservatively.

## Standard route: 2 calls

1. Call `im-not-ai.humanize-diagnostician` once. Pass absolute
   `input_path=<.../01_input_with_metrics.txt>`,
   `taxonomy_path=<.../references/diagnosis-rules.md>`, and
   `output_path=<.../02_diagnosis.md>`.
2. Re-run the shim with `--diagnosis _workspace/<run_id>/02_diagnosis.md`.
3. Call `im-not-ai.humanize-monolith` once with the regenerated combined input,
   absolute quick-rules path, genre, and `output_path=<.../final.md>`.
4. Run the Phase 2.5 gate. Add the finalizer only for a 30-50% warning, two or
   more self-check failures, or an explicit request for verification evidence.

## Heavy route: 3 or more calls

1. Call the diagnostician as in standard.
2. Re-run the shim with `--diagnosis ... --chunk`.
3. Read `chunk_manifest.json`. If it has one body chunk, call the monolith once
   with that manifest's `input_file`. If it has two or more body chunks, call
   `im-not-ai.humanize-monolith` once per body chunk using the manifest's exact
   `input_file` and `rewritten_file` values. Use one `subagent` parallel request
   with `concurrency: 4`; never construct chunk names yourself.
4. For multiple chunks run:

```bash
python3 <PACKAGE_ROOT>/scripts/reassemble_chunks.py \
  --run-dir _workspace/<run_id>
```

   Use the resulting `03_reassembled.md` as `final.md` for the gate. For one
   chunk, the monolith writes `final.md` directly.
5. Run the Phase 2.5 gate.
6. Call `im-not-ai.humanize-finalizer` with absolute
   `original_path=<.../01_input.txt>`, `rewritten_path=<.../final.md>`,
   `diagnosis_path=<.../02_diagnosis.md>`, and output paths for `final.md` and
   `09_finalize.json`. It must make only local corrections.
7. Run the gate again after finalization.

## Phase 2.5: deterministic gate

Run this after every monolith output and once more after finalization when used:

```bash
python3 <PACKAGE_ROOT>/scripts/verify_gates.py \
  --before _workspace/<run_id>/01_input.txt \
  --after _workspace/<run_id>/final.md \
  --genre <genre>
```

Use its exit code and output as the source of truth. Exit 0 passes. Exit 1 is a
warning and normally promotes standard/light to finalizer. Exit 2 rejects the
output at 50% or more and requires one conservative retry. Exit 3 means the
inputs are invalid and must be fixed; never skip the gate.

## Output

Return the same concise four-part report as the single-call skill. Keep the
rewritten body in `_workspace/<run_id>/final.md`, including its
`HUMANIZE-SUMMARY` comment. Report the gate's measured change rate, grade,
self-check count, route, and any residual finding. If grade B or lower, recommend
heavy verification. Do not inline the full document unless the user asks for it.

## Follow-up commands

- `/humanize` invokes this skill with the supplied text or file argument.
- `/humanize-redo` uses the latest run's `final.md` as the next input and forces
  the heavy route.
- A request to change one category or one paragraph also forces heavy and keeps
  the edit local.
