# Contributing to django-schemaform

Thank you for your interest in contributing! This guide will help you get set up for development.

## Prerequisites

- **Python 3.12+** — The project supports Python 3.12, 3.13, and 3.14
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager
- **[just](https://just.systems/)** — Command runner (optional but recommended)

## Getting Started

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/YOUR_USERNAME/django-schemaform.git
   cd django-schemaform
   ```

2. **Install dependencies:**

   ```bash
   uv sync --group dev
   ```

3. **Install Playwright browsers** (required for browser tests):

   ```bash
   just install-playwright
   # or: uv run playwright install chromium
   ```

4. **Install pre-commit hooks:**

   ```bash
   uv run pre-commit install
   ```

## Pre-commit Hooks

This project uses pre-commit to ensure code quality. The following hooks run automatically on each commit:

| Hook | Purpose |
|------|---------|
| **ruff check** | Linting with auto-fix |
| **ruff format** | Code formatting |
| **ty** | Type checking |
| **pytest-testmon** | Run affected tests |
| **check-json/toml/yaml** | Validate config files |
| **check-added-large-files** | Prevent large file commits |
| **uv-lock** | Keep lock file in sync |

If any hook fails, the commit will be blocked. Fix the issues and try again.

To run hooks manually on all files:

```bash
uv run pre-commit run --all-files
```

## Running Tests

**Quick test run:**

```bash
uv run pytest
```

**Run tests across all supported Python versions:**

```bash
just test
```

**Run only browser tests:**

```bash
uv run pytest -m playwright
```

**Skip browser tests:**

```bash
uv run pytest -m "not playwright"
```

Tests are located in `src/schemaform/tests/`.

## Running the Demo App

To manually test changes in a real Django application:

```bash
just run-demo
```

This syncs dependencies, runs migrations, and starts the development server. Visit http://localhost:8000 to see the demo forms.

## Making Changes

1. **Create a branch** for your changes:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and add tests for new functionality.

3. **Run the test suite** to ensure everything passes:

   ```bash
   uv run pytest
   ```

4. **Commit your changes.** Pre-commit hooks will run automatically.

5. **Push and open a pull request** against the `main` branch.

## Pull Request Guidelines

- Keep PRs focused on a single change
- Add tests for new features or bug fixes
- Update documentation if needed
- Ensure all pre-commit hooks pass
- Reference any related issues in the PR description

## Available Just Commands

Run `just` to see all available commands:

| Command | Description |
|---------|-------------|
| `just install-playwright` | Install Playwright browsers |
| `just test` | Run tests on Python 3.12, 3.13, and 3.14 |
| `just run-demo` | Run the demo Django application |

## Questions?

Open an issue if you have questions or run into problems.
