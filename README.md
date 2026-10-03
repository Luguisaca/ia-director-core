# IA Director Core

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
git clone <REPOSITORY-URL>
cd ia-director-core
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps .
```

### Ubuntu / Debian

```sh
git clone <REPOSITORY-URL>
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

## CLI smoke test

The current CLI exposes a deterministic demo capability:

```powershell
.\.venv\Scripts\ia-director.exe "demo: smoke test" --records-dir .ia-director/records --authorize --authorized-by pilot-human --scope builtin.intent_digest --risk-tier low
```

Expected status: `HUMAN_TEST_PENDING`. Missing identity, authorization or exact capability scope must fail closed.

The directed Python interfaces provide the broader contract/selection/authorization/execution/verification path used by the test suite. The CLI demo should not be interpreted as the full capability surface.

## Security and assurance

The software is experimental. Do not infer authorization from technical access, capability metadata or model/tool output. Do not use it for privileged, destructive, remote or sensitive workloads without separately validating the relevant controls for that environment.

See `docs/ASSURANCE.md` for current public assurance boundaries.

## License

IA Director Core is licensed under **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`).

Required Notice: Copyright 2026 Luis Salamanca / LUGUISACA

Noncommercial use, modification and distribution are subject to the license terms. Commercial use is not granted by this public license. See `LICENSE`.
