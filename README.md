# Omphalos

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)
[![CI](https://github.com/snui1s/Omphalos/actions/workflows/ci.yml/badge.svg)](https://github.com/snui1s/Omphalos/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Codebase symbol indexer for LLMs.

Omphalos generates a compact, high-signal symbol map (`INDEX.md`) of your repository. It provides large language models and developers with an instant architectural overview and precise symbol locations—minimizing token usage and eliminating the need to read entire source files just to find declarations.

## Table of Contents

- [Omphalos](#omphalos)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
  - [Install](#install)
  - [Usage](#usage)
    - [Quick Start](#quick-start)
    - [CLI Reference](#cli-reference)
    - [LLM / Agent Integration](#llm--agent-integration)
  - [Development](#development)
  - [Related Efforts](#related-efforts)
  - [Maintainers](#maintainers)
  - [Contributing](#contributing)
  - [License](#license)

## Background

When providing a full codebase as context to Large Language Models (LLMs) or AI coding agents, feeding entire file contents quickly exhausts the model's context window, degrades reasoning performance, and incurs high token costs.

In practice, an agent rarely needs the implementation bodies of every file at once; it only needs an accurate structural index: what functions, classes, interfaces, and methods exist, where they are defined, and what their docstrings say.

Omphalos was created to solve this problem:

1. **Multi-language AST Parsing**: Uses Tree-sitter for deterministic parsing across Python, TypeScript/JavaScript, Go, and Rust.
2. **Precise Line Numbers (`@<line>`)**: Symbols indicate exact declaration line numbers so agents can inspect or slice specific ranges on demand.
3. **Internal Logic Hints**: Function-like symbols list their deduplicated call targets (`calls`) and raised exception types (`raises`), giving agents a control-flow preview without opening the file.
4. **Atomic Incremental Cache**: Tracks SHA-256 content hashes to re-parse only changed files, guaranteeing rapid re-indexes.
5. **CI/CD Integration**: Supports `--check` mode to ensure codebase indexes stay synchronized with changes.
6. **Live Watch Mode**: Zero-dependency file monitoring (`omph watch`) automatically re-indexes in milliseconds whenever code files are edited or saved.

## Install

### Using [uv](https://github.com/astral-sh/uv) (Recommended)

Run directly without installing:

```sh
$ uvx --from git+https://github.com/snui1s/Omphalos.git omph scan
```

Or install as a standalone CLI tool:

```sh
$ uv tool install git+https://github.com/snui1s/Omphalos.git
```

### Using pip

```sh
$ pip install git+https://github.com/snui1s/Omphalos.git
```

### Using npm / npx

Run directly via npx:

```sh
$ npx omphalos scan
```

Or install globally:

```sh
$ npm install -g omphalos
```

### From Source

```sh
$ git clone https://github.com/snui1s/Omphalos.git
$ cd Omphalos
$ uv sync
```

## Usage

### Quick Start

1. **Initialize Ignore File** (creates default `.omphignore`):

```sh
$ omph init
```

2. **Generate the Symbol Index**:

```sh
$ omph scan
```

This generates `INDEX.md` in the root directory:

```markdown
# Codebase Symbol Index

## src/omphalos/cache.py

- `calculate_sha256()` @15: Calculate the SHA-256 checksum of raw file bytes for change detection. (calls: `hexdigest`, `hashlib.sha256`)
- `save_cache()` @38: Save symbol cache to .omphcache atomically. (calls: `tempfile.mkstemp`, `os.fdopen`, `json.dump`, `os.replace`, `os.unlink`)

## src/omphalos/cli.py

- `_version_callback()` @33: Callback for --version flag to print the version and exit immediately. (calls: `typer.echo`, `_package_version`; raises: `typer.Exit`)

## tests/fixtures/sample.ts

- export interface `UserProfile` @1
- export type `AuthToken` @6
- export function `verifyToken()` @8
- export class `SessionManager` @18
  - `createSession()` @19
```

3. **Keep Index Synchronized in Real Time** (Optional):

Run Watch Mode in a background terminal to automatically update `INDEX.md` on every file save:

```sh
$ omph watch
# or: omph scan -w
```

4. **Instruct AI Agents via `AGENTS.md`**:

Create or add to `AGENTS.md` (or `CLAUDE.md` / `.cursorrules`) at the root of your repository so AI agents read `INDEX.md` before exploring code:

```markdown
# Agent Guidelines

## Codebase Navigation & Exploration

Before searching, running grep, or opening entire source files across the codebase:

1. **Always read [`INDEX.md`](INDEX.md) first.** It provides an instant symbol map of the entire repository with exact line numbers.
2. Use the symbols, line locations (`@<line>`), and internal logic hints (`calls:`, `raises:`) in [`INDEX.md`](INDEX.md) to pinpoint definitions directly.
3. Inspect or slice-read only the specific line ranges or files needed for the task, rather than loading entire files into context.
```

### CLI Reference

```sh
$ omph scan [DIRECTORY] [OPTIONS]
$ omph watch [DIRECTORY] [OPTIONS]
```

The binary is installed as `omph`; the full name `omphalos` is also available as an alias.

| Option           | Flag               | Description                                                               |
| ---------------- | ------------------ | ------------------------------------------------------------------------- |
| `--watch`, `-w`  | flag               | Watch files for changes and re-index incrementally in real time.          |
| `--output`, `-o` | `PATH`             | Custom path for index output (default: `INDEX.md`).                       |
| `--format`       | `markdown \| json` | Output format (default: `markdown`).                                      |
| `--check`        | flag               | Verify index is up to date without writing. Exits with code `1` if stale. |
| `--git-only`     | flag               | Scan only files tracked by Git (`git ls-files`).                          |
| `--no-cache`     | flag               | Bypass cache and re-parse all files.                                      |
| `--version`      | flag               | Show version and exit.                                                    |
| `--help`         | flag               | Show help message.                                                        |

### LLM / Agent Integration

- **Automatic Agent Discovery via `AGENTS.md`**: Coding agents (Antigravity, Cursor, Claude Code, GitHub Copilot) automatically load `AGENTS.md` at conversation start. By telling the agent to consult `INDEX.md` first, the agent pinpoints definitions immediately without burning tokens on repository-wide grep searches.
- **Surgical Inspection**: Because each symbol includes `@<line>`, an LLM can request precise lines via tools (e.g. `head -n 50` or view tool slice) rather than ingesting entire files.
- **Machine-Readable Formats**: Use `--format json` to integrate with custom RAG systems or agent tools:

```sh
$ omph scan --format json -o index.json
```

## Development

```sh
# Install development dependencies
$ uv sync --dev

# Run tests
$ uv run pytest

# Run linter and type checker
$ uv run ruff check .
$ uv run mypy src
```

## Related Efforts

- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - Fast, incremental parsing system used under the hood.
- [Universal Ctags](https://ctags.io/) - Traditional code indexing system.
- [Repomix](https://github.com/yamadashy/repomix) - Repository packager for AI context.

## Contributing

Feel free to dive in! [Open an issue](https://github.com/snui1s/Omphalos/issues/new) or submit a Pull Request.

Omphalos follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) Code of Conduct.

## License

[MIT](LICENSE) © 2026 snui1s
