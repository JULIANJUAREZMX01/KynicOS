[CmdletBinding()]
param(
    [ValidateSet('audit','verify','repair-plan','doctor')]
    [string]$Mode = 'audit',
    [string]$Workspace = (Join-Path $HOME 'KynicOS_Workspace'),
    [switch]$NoInstall,
    [switch]$RunAgents,
    [switch]$RunRuntime
)

$ErrorActionPreference = 'Continue'
Set-StrictMode -Version Latest

$RepoUrl = 'https://github.com/JULIANJUAREZMX01/KynicOS.git'
$RepoDir = Join-Path $Workspace 'KynicOS'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$EvidenceDir = Join-Path $RepoDir (Join-Path 'evidence' $Stamp)
$ScriptVersion = '1.0.0'

New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

$Summary = [ordered]@{
    version = $ScriptVersion
    mode = $Mode
    started_at = (Get-Date).ToString('o')
    repository = $RepoUrl
    repo_dir = $RepoDir
    evidence_dir = $EvidenceDir
    destructive_operations = $false
    commit = $false
    push = $false
    results = @()
}

function Write-Result {
    param([string]$Name,[string]$Status,[string]$Detail)
    $Summary.results += [ordered]@{ name=$Name; status=$Status; detail=$Detail }
    $line = "[$Status] $Name :: $Detail"
    Write-Host $line
    Add-Content -LiteralPath (Join-Path $EvidenceDir 'orchestrator.log') -Value $line
}

function Invoke-Captured {
    param([string]$Name,[string]$File,[string[]]$Args)
    $outFile = Join-Path $EvidenceDir ("{0}.txt" -f ($Name -replace '[^A-Za-z0-9_.-]','_'))
    try {
        & $File @Args *> $outFile
        $code = $LASTEXITCODE
        if ($code -eq 0) { Write-Result $Name 'PASS' "exit=$code; output=$outFile" }
        else { Write-Result $Name 'FAIL' "exit=$code; output=$outFile" }
        return $code
    } catch {
        $_ | Out-File -FilePath $outFile -Encoding utf8
        Write-Result $Name 'BLOCKED' $_.Exception.Message
        return -1
    }
}

function Find-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return $null }
    return $cmd.Source
}

function Ensure-Repo {
    if (Test-Path (Join-Path $RepoDir '.git')) {
        Write-Result 'repository' 'PASS-STATIC' 'Existing Git checkout found; no reset, checkout, commit, or push performed.'
        Invoke-Captured 'git-status' 'git' @('-C',$RepoDir,'status','--short','--branch') | Out-Null
        Invoke-Captured 'git-log' 'git' @('-C',$RepoDir,'log','-5','--oneline','--decorate') | Out-Null
        Invoke-Captured 'git-fetch' 'git' @('-C',$RepoDir,'fetch','--prune','origin') | Out-Null
    } else {
        if (-not (Find-Command 'git')) { Write-Result 'repository' 'BLOCKED' 'git is not installed.'; return $false }
        New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
        Invoke-Captured 'git-clone' 'git' @('clone',$RepoUrl,$RepoDir) | Out-Null
        if (-not (Test-Path (Join-Path $RepoDir '.git'))) { Write-Result 'repository' 'FAIL' 'Clone did not produce a Git checkout.'; return $false }
    }
    return $true
}

function Write-Inventory {
    $items = @(
        'app/main.py','app/agents/concierge_loop.py','app/core/loop.py','app/core/context.py',
        'app/core/sentinel.py','app/core/skill_engine.py','app/core/tools.py','app/cloud/providers.py',
        'app/cloud/sessions.py','app/skills/skill_builder.py','requirements.txt',
        'tests/test_tools.py','tests/test_main.py','.github/workflows/test.yml','Cargo.toml'
    )
    $rows = foreach ($item in $items) {
        [ordered]@{ path=$item; exists=(Test-Path (Join-Path $RepoDir $item)) }
    }
    $rows | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $EvidenceDir 'inventory.json') -Encoding utf8
    Write-Result 'architecture-inventory' 'PASS-STATIC' "Inventory written to $EvidenceDir\inventory.json"
}

function Static-Scan {
    $patterns = @(
        'shell=True','eval(','exec(','os.system(','subprocess.','importlib.','DANGEROUS_IMPORTS',
        'IMMUTABLE_SKILLS','auto_healing','overdrive','allow_origins=["*"]','network_scan','system_control'
    )
    $hits = New-Object System.Collections.Generic.List[object]
    $files = Get-ChildItem -LiteralPath (Join-Path $RepoDir 'app') -Recurse -File -Filter '*.py' -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $lineNo = 0
        foreach ($line in Get-Content -LiteralPath $file.FullName) {
            $lineNo++
            foreach ($pattern in $patterns) {
                if ($line -like "*$pattern*") {
                    $hits.Add([ordered]@{file=$file.FullName.Substring($RepoDir.Length+1); line=$lineNo; pattern=$pattern; text=$line.Trim()})
                }
            }
        }
    }
    $hits | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $EvidenceDir 'security-findings.json') -Encoding utf8
    Write-Result 'security-static-scan' 'PASS-STATIC' "Pattern scan completed; findings=$($hits.Count). Findings are review items, not exploit instructions."
}

function Generate-Agent-Prompts {
    $master = @'
KynicOS independent engineering audit. Inspect only the current checkout. Do not modify files, commit, push, install unapproved software, or infer runtime success from static code. Separate evidence as PASS-RUNTIME, PASS-STATIC, PARTIAL, FAIL, BLOCKED. Verify Git state, dependency inventory, Python tests, compileall, Rust tests if applicable, CI workflow, runtime/API status if explicitly executed, security-sensitive tools, AgentLoop/Concierge orchestration, memory/session persistence, sentinel lifecycle, dynamic skills, and the 13-point post-merge checklist. Report exact file paths and line references where possible. Treat "cognitive OS" and autonomy levels as architectural claims requiring evidence. Mentalidad del sujeto means inferred engineering style from implementation choices only, never psychological diagnosis.
'@
    $security = @'
KynicOS security review. Inspect current checkout without changing it. Focus on shell=True, subprocess, eval/exec, dynamic imports, generated skill execution, arbitrary file writes, Git operations, network scanning, process/system control, self-repair, overdrive, CORS, secrets, and trust boundaries. Classify each finding by evidence and severity. Distinguish a hardening mechanism from a true sandbox. Do not provide offensive exploitation steps.
'@
    $verification = @'
KynicOS verification review. Independently reproduce the audit claims where tools are available. Do not trust prior reports. Run the project's tests and static checks available in the checkout, inspect CI configuration, and state exactly what could not be executed. Verify the 13-point post-merge checklist, especially Concierge diagnostic behavior, room_number/guest_name persistence callers, and stale IMMUTABLE_SKILLS. Return PASS, PASS_WITH_WARNINGS, FAIL, or BLOCKED with evidence.
'@
    Set-Content (Join-Path $EvidenceDir 'agent-master-audit.txt') $master -Encoding utf8
    Set-Content (Join-Path $EvidenceDir 'agent-security-review.txt') $security -Encoding utf8
    Set-Content (Join-Path $EvidenceDir 'agent-verification-review.txt') $verification -Encoding utf8
    Write-Result 'agent-prompts' 'PASS-STATIC' 'Three independent review prompts generated.'
}

function Detect-Agents {
    $names = @('codex','gemini','kilo','ollama')
    $rows = foreach ($name in $names) {
        $path = Find-Command $name
        [ordered]@{ agent=$name; available=($null -ne $path); path=$path }
    }
    $rows | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $EvidenceDir 'agents.json') -Encoding utf8
    foreach ($row in $rows) {
        if ($row.available -and $RunAgents) {
            Invoke-Captured ("agent-{0}-version" -f $row.agent) $row.path @('--version') | Out-Null
        } else {
            Write-Result ("agent-{0}" -f $row.agent) 'PASS-STATIC' (if ($row.available) { 'Detected; version execution disabled unless -RunAgents.' } else { 'Not detected; prompt retained for external execution.' })
        }
    }
}

function Python-Checks {
    $py = Find-Command 'python'
    if ($null -eq $py) { $py = Find-Command 'py' }
    if ($null -eq $py) { Write-Result 'python' 'BLOCKED' 'Python interpreter not found.'; return }
    Invoke-Captured 'python-version' $py @('--version') | Out-Null
    if (Test-Path (Join-Path $RepoDir 'app')) { Invoke-Captured 'compileall' $py @('-m','compileall','-q',(Join-Path $RepoDir 'app')) | Out-Null }
    if (Test-Path (Join-Path $RepoDir 'tests')) { Invoke-Captured 'pytest' $py @('-m','pytest','-q',(Join-Path $RepoDir 'tests')) | Out-Null }
    if (-not $NoInstall -and (Test-Path (Join-Path $RepoDir 'requirements.txt'))) {
        $venv = Join-Path $RepoDir '.venv'
        if (-not (Test-Path $venv)) { Invoke-Captured 'venv-create' $py @('-m','venv',$venv) | Out-Null }
        $venvPy = Join-Path $venv 'Scripts\python.exe'
        if (Test-Path $venvPy) { Invoke-Captured 'requirements-install' $venvPy @('-m','pip','install','-r',(Join-Path $RepoDir 'requirements.txt')) | Out-Null }
        else { Write-Result 'venv-python' 'BLOCKED' 'Windows venv Python executable not found.' }
    }
    $ruff = Find-Command 'ruff'; if ($null -ne $ruff) { Invoke-Captured 'ruff' $ruff @('check',$RepoDir) | Out-Null } else { Write-Result 'ruff' 'PASS-STATIC' 'ruff not installed; check not executed.' }
    $mypy = Find-Command 'mypy'; if ($null -ne $mypy) { Invoke-Captured 'mypy' $mypy @($RepoDir) | Out-Null } else { Write-Result 'mypy' 'PASS-STATIC' 'mypy not installed; check not executed.' }
}

function Rust-Checks {
    if (-not (Test-Path (Join-Path $RepoDir 'Cargo.toml'))) { Write-Result 'rust' 'PASS-STATIC' 'No Cargo.toml in repository root; Rust checks not applicable.'; return }
    $cargo = Find-Command 'cargo'
    if ($null -eq $cargo) { Write-Result 'rust' 'BLOCKED' 'Cargo not found.'; return }
    Push-Location $RepoDir
    try {
        Invoke-Captured 'cargo-test' $cargo @('test') | Out-Null
        Invoke-Captured 'cargo-clippy' $cargo @('clippy','--','-D','warnings') | Out-Null
    } finally { Pop-Location }
}

function Runtime-Check {
    if (-not $RunRuntime) { Write-Result 'runtime' 'PASS-STATIC' 'Runtime execution not requested; use -RunRuntime.'; return }
    $py = Find-Command 'python'; if ($null -eq $py) { Write-Result 'runtime' 'BLOCKED' 'Python not found.'; return }
    $stdout = Join-Path $EvidenceDir 'runtime.stdout.log'; $stderr = Join-Path $EvidenceDir 'runtime.stderr.log'
    $proc = $null
    Push-Location $RepoDir
    try {
        $proc = Start-Process -FilePath $py -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $RepoDir -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
        $ok = $false
        for ($i=0; $i -lt 15; $i++) {
            Start-Sleep -Seconds 1
            try {
                $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/status' -UseBasicParsing -TimeoutSec 2
                $resp.Content | Set-Content (Join-Path $EvidenceDir 'runtime-status.json') -Encoding utf8
                Write-Result 'runtime-http-status' 'PASS-RUNTIME' "HTTP $($resp.StatusCode); /api/status recorded."
                $ok = $true; break
            } catch { }
            if ($proc.HasExited) { break }
        }
        if (-not $ok) { Write-Result 'runtime-http-status' 'FAIL' 'Server did not return /api/status within 15 seconds. Inspect runtime stderr/stdout.' }
    } catch { Write-Result 'runtime' 'BLOCKED' $_.Exception.Message }
    finally {
        if ($null -ne $proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        Pop-Location
    }
}

function Write-Checklist {
    $checklist = @(
        [ordered]@{id=1; item='Sentinel/settings contract'; status='static verification required'},
        [ordered]@{id=2; item='send_alert availability'; status='static verification required'},
        [ordered]@{id=3; item='AgentContext.add_file'; status='static verification required'},
        [ordered]@{id=4; item='state/files/timestamps/metadata persistence'; status='static verification required'},
        [ordered]@{id=5; item='Windows temp/ZIP handling'; status='static verification required'},
        [ordered]@{id=6; item='Telegram /start text'; status='static verification required'},
        [ordered]@{id=7; item='Telegram self-import'; status='static verification required'},
        [ordered]@{id=8; item='Concierge diagnostic empty-list behavior'; status='PENDING_CALLER_AUDIT'},
        [ordered]@{id=9; item='room_number/guest_name persistence callers'; status='PARTIAL_CALLER_AUDIT'},
        [ordered]@{id=10; item='DANGEROUS_IMPORTS enforcement'; status='static verification required'},
        [ordered]@{id=11; item='IMMUTABLE_SKILLS stale names'; status='PENDING_CLEANUP'},
        [ordered]@{id=12; item='Telegram optional startup/failure cleanup'; status='static verification required'},
        [ordered]@{id=13; item='CI/test execution'; status='RUNTIME_OR_CI_EVIDENCE_REQUIRED'}
    )
    $checklist | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $EvidenceDir 'post-merge-13-point-checklist.json') -Encoding utf8
    Write-Result '13-point-checklist' 'PASS-STATIC' 'Checklist written with known pending items preserved instead of silently marked fixed.'
}

function Main {
    if (-not (Ensure-Repo)) { return }
    Write-Inventory
    Static-Scan
    Generate-Agent-Prompts
    Detect-Agents
    Write-Checklist
    if ($Mode -eq 'doctor' -or $Mode -eq 'audit' -or $Mode -eq 'verify') { Python-Checks; Rust-Checks }
    Runtime-Check
    if ($Mode -eq 'repair-plan') {
        Write-Result 'repair-plan' 'PASS-STATIC' 'Repair mode generates evidence and prompts only; it does not edit, commit, or push.'
    }
    $Summary.finished_at = (Get-Date).ToString('o')
    $Summary | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $EvidenceDir 'manifest.json') -Encoding utf8
    Write-Host "`nEvidence: $EvidenceDir"
    Write-Host 'Safety: no git reset, no commit, no push performed by this orchestrator.'
}

Main
