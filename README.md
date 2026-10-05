# IA Director Core

**English** · [Español](README.es.md)

IA Director Core is an experimental, provider-independent Python core for turning an explicit work contract into bounded execution with authorization, verification and evidence.

The current software can:

- represent outcomes, acceptance criteria, targets, effects, data destinations, risk and cost constraints;
- discover and evaluate bounded capability descriptions;
- keep human authorization separate from capability selection;
- bind execution to capability, target, effects, destinations and risk;
- require action-bound approval for material-risk actions;
- execute local processes without shell interpolation and with timeout/output bounds;
- verify bounded results independently from execution success;
- minimize raw payload/result persistence;
- preserve interrupted state without silently reporting completion.

Python 3.11+; no third-party runtime dependencies.

## Install

Clone the repository and use an isolated Python environment.

### Windows

```powershell
git clone https://github.com/Luguisaca/ia-director-core.git
cd ia-director-core
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps .
```

You do **not** need to activate the virtual environment on Windows. The documented commands call the executables inside `.venv` directly, so PowerShell execution policy does not need to be changed. If `Activate.ps1` is blocked, skip activation and continue with the direct `.venv\Scripts\...` commands below. Do not disable or weaken the machine's execution policy just to run IA Director.

### Ubuntu / Debian

```sh
git clone https://github.com/Luguisaca/ia-director-core.git
cd ia-director-core
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps .
```

A packaged virtual-environment install requires the operating system to provide Python's `venv`/pip support.

## Verify the installation

```sh
python -m unittest discover -s tests -v
```

The repository test suite is the executable regression baseline. Passing it demonstrates only the properties covered by those tests; it is not a security, privacy, compliance or production certification.

## Intent entry

Run IA Director with the outcome you want:

```powershell
.\.venv\Scripts\ia-director.exe "Create a small application that does X"
```

The CLI asks only for authority it actually needs: project-local modification, persistent tool acquisition when no supported development runtime is available, provider authentication when required, and provider data use. On supported Windows hosts it can use Windows Package Manager to acquire a missing Node.js prerequisite and npm to acquire the currently demonstrated Codex adapter after explicit approval. Authentication remains human-owned.

A successful machine-verified development run reaches `HUMAN_TEST_PENDING`; that means the generated solution is ready for human usefulness testing, not that IA Director or the generated product is generally secure, compliant or production-ready.

The runtime adapter is replaceable. Codex is the currently demonstrated development adapter, not an architectural dependency. If no supported acquisition path exists, the software fails closed rather than inventing capability.

For the earlier deterministic core demo, add `--legacy-demo` with its explicit scope/risk arguments.

## Security and assurance

The software is experimental. Do not infer authorization from technical access, capability metadata or model/tool output. Do not use it for privileged, destructive, remote or sensitive workloads without separately validating the relevant controls for that environment.

See `docs/ASSURANCE.md` for current public assurance boundaries.

## License

IA Director Core is licensed under **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`).

Required Notice: Copyright 2026 Luis Salamanca / LUGUISACA

Noncommercial use, modification and distribution are subject to the license terms. Commercial use is not granted by this public license. See `LICENSE`.
