# Contributing to ARYx AGENT

Thank you for contributing to ARYx AGENT! Our goal is to maintain the zero-friction experience for every terminal user.

## Core Rules for Contributions

1. **Zero Silent Failures**: Every error must explain what happened, why it happened, and provide an actionable fix command (e.g. `Run aryx doctor for help`).
2. **Never Expose Secrets**: Redact API keys from logs, prints, and error messages using `aryx.config.redact_secrets()`.
3. **Idempotence**: Installers and tools must be safe to run multiple times without corrupting system state.
4. **Safety by Default**: Any new write tools must integrate with `create_snapshot()` and respect approval modes.

## Local Development & Testing

1. Clone the repository:
   ```bash
   git clone https://github.com/aryx-agent/aryx-agent
   cd aryx-agent
   ```

2. Run the test suite:
   ```bash
   PYTHONPATH=. python3 tests/test_providers.py
   PYTHONPATH=. python3 tests/test_doctor.py
   PYTHONPATH=. python3 tests/test_memory.py
   ```

3. Test doctor checks:
   ```bash
   python3 -m aryx.cli doctor
   ```

## Pull Request Guidelines

- Ensure all existing unit tests pass.
- Write clear docstrings for new provider adapters or tools.
- Keep dependencies minimal to guarantee frictionless installs on standard developer machines.
