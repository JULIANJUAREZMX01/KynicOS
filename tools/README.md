# KynicOS Orchestrator

`tools/kynicos.ps1` is a Windows PowerShell 5.1+/7+ orchestration script for reproducible repository audit and verification.

## Design goals

- Audit before repair.
- Evidence before conclusions.
- Runtime evidence is never inferred from static inspection.
- No destructive Git operations.
- No automatic commit or push.
- Optional runtime execution is isolated to `127.0.0.1:8765` and `/api/status`.
- External agent CLIs are detected but their command syntax is not assumed.

## Modes

```powershell
.\tools\kynicos.ps1 -Mode audit
.\tools\kynicos.ps1 -Mode verify
.\tools\kynicos.ps1 -Mode doctor
.\tools\kynicos.ps1 -Mode repair-plan
```

Optional switches:

```powershell
-NoInstall     # do not create .venv or install requirements.txt
-RunAgents     # run --version only for detected Codex/Gemini/Kilo/Ollama CLIs
-RunRuntime    # start uvicorn locally and verify /api/status
-Workspace     # override the default workspace directory
```

Example:

```powershell
.\tools\kynicos.ps1 -Mode verify -NoInstall -RunRuntime
```

## Evidence

Each execution writes to:

```text
<repo>\evidence\YYYYMMDD_HHMMSS\
```

Artifacts include:

- `manifest.json`
- `orchestrator.log`
- `inventory.json`
- `security-findings.json`
- Python/Rust command outputs
- runtime stdout/stderr and `/api/status` response when requested
- independent audit/security/verification prompts
- `post-merge-13-point-checklist.json`

## Safety contract

The orchestrator does **not** run `git reset --hard`, overwrite an existing checkout through destructive checkout operations, commit changes, or push changes. `-Mode repair-plan` is deliberately evidence-only; actual repair remains a separate controlled workflow.

The security scan is a static review aid. A finding such as `shell=True`, `subprocess`, or `overdrive` is not automatically a vulnerability; it is evidence requiring contextual review.

## Agent orchestration

The script prepares prompts for independent reviewers and records availability of `codex`, `gemini`, `kilo`, and `ollama`. It only invokes `--version` when `-RunAgents` is explicitly supplied because CLI interfaces vary by installation/version. The generated prompts are intended to be executed by the corresponding tools or by a human reviewer and then consolidated into a consensus artifact.

## Current repository-specific checks

The current branch contains fixes for the previously identified Concierge diagnostic crash path, durable `room_number` / `guest_name` context properties, and stale `IMMUTABLE_SKILLS` registry entries. The orchestrator checklist should therefore treat those items as static-fixed and reserve runtime/CI execution for independent evidence.

Remaining verification focus:

- Verify the Concierge regression test against the installed dependency set.
- Verify callers populate `room_number` / `guest_name` from the actual channel/session flow where required.
- Verify Sentinel startup/shutdown behavior at runtime.
- Verify CI/test execution with an actual workflow run or local execution.
- Review the remaining security-sensitive operational tools and trust boundaries.

This tool is an orchestrator, not proof that the repository is production-ready. A `PASS-STATIC` result means only that the corresponding static action completed.
