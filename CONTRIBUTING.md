# Contributing to IA Director Core

Thank you for your interest in improving IA Director Core.

## Before contributing

IA Director Core is experimental software. Contributions must preserve explicit authorization, bounded execution, independent verification and evidence. Technical capability or access must never be treated as human authority.

Do not include secrets, credentials, personal/customer data, private environment evidence, internal project notes or material from systems you are not authorized to use.

## Development

Use Python 3.11 or newer in an isolated environment.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps .
python -m unittest discover -s tests -v
```

On Windows, activate/use the virtual environment with the corresponding `.venv\Scripts\python.exe` path.

Keep changes focused and include regression coverage for behavioral changes. A passing suite demonstrates only the properties covered by those tests.

## Pull requests

Open a focused pull request against `main`. Explain:

- what changed and why;
- how it was validated;
- any security, authorization, privacy, compatibility or persistence impact;
- known limitations.

Do not broaden capability scope, target scope, effects, data destinations or risk semantics silently.

## Architecture and assurance

Public contributions should work within the boundaries described by `README.md`, `docs/ASSURANCE.md` and `SECURITY.md`. Changes that alter trust boundaries, authorization semantics, privileged/destructive execution, remote administration, identity, persistence or external data handling require explicit design and security review.

## Security reports

Do not disclose suspected vulnerabilities through public issues or pull requests. Follow `SECURITY.md` for private reporting.

## License

IA Director Core is distributed under PolyForm Noncommercial License 1.0.0. Contributions and use are subject to `LICENSE`; public repository access does not grant additional commercial rights.
