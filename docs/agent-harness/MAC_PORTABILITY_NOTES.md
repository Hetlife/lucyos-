# Future Apple Silicon macOS
Code additions use Python stdlib + optional jsonschema (fail-closed if absent), pathlib and git. No GNU-only flags or absolute home paths in code; Linux user paths occur in evidence/documented operator command examples only.
Use aion_core/host/macos.py and platform resolver when deploying on Mac; retain Linux host adapter and Lucy-den fallback. Validate dependency installation, git availability, secrets storage, path case/normalization, process supervision and file permissions before first Mac live deployment. No Mac hardware assumed available.
