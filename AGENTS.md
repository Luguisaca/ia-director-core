# Development guidance

This repository contains IA Director Core software.

When changing the code:

- preserve explicit authorization and fail-closed behavior;
- never treat capability metadata or technical access as human authority;
- keep target, effects, data destinations and risk constraints explicit;
- avoid adding runtime dependencies or infrastructure without a product requirement;
- do not persist secrets or sensitive payloads unnecessarily;
- keep execution bounded and verification distinct from execution success;
- run `python -m unittest discover -s tests -v` after changes;
- do not commit runtime records, credentials, caches or local environments.

Project research, internal decisions, experiments and private operational state are intentionally not stored in this distributable repository.
