# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `--calls/--no-calls` option on `scan` and `watch`. `--no-calls` omits `calls:` annotations
  (about half the index size on large codebases); `raises:` is kept. The cache is unaffected,
  so the flag can be toggled without re-parsing. (#3)
- README sections on index size for large codebases and on update notifications / privacy,
  including the existing `OMPH_NO_UPDATE_NOTIFIER=1` opt-out.
- Test for the `OMPH_NO_UPDATE_NOTIFIER` opt-out.
- Coverage reporting in CI (`pytest-cov`, fails under 88%; currently ~92%).
- Weekly "Dependency canary" workflow that runs the tests against the newest dependency versions
  allowed by `pyproject.toml`, ignoring `uv.lock`.

### Changed
- Runtime dependencies now have upper bounds (`typer<1`, `pathspec<2`, each `tree-sitter*` package
  capped below its next minor, since they are pre-1.0 and minor releases can break the API).

## [1.2.1] - 2026-10-09

### Added
- Tag-triggered release workflow: runs CI, checks that the tag matches `pyproject.toml` and
  `package.json`, builds, then publishes to PyPI and npm. (#2)
- CI job that tests the npm wrapper on Linux, macOS and Windows.
- Tests for `bin/omph.js`.

### Fixed
- npm wrapper: npm shims were detected by substring, so any path containing `npm` was rejected
  (e.g. `C:\Users\npmfan\...`). Matching is now by whole path segment. (#2)
- npm wrapper: on POSIX a symlink resolving to the wrapper itself could make it call itself
  recursively. Real paths are now compared. (#2)

## [1.2.0] - 2026-10-08

### Added
- Watch mode (`omph watch`, `omph scan --watch`) that re-indexes on file changes.
- Update notifications (checks PyPI at most once per 24 hours; skipped in CI and for
  `--format json` / `--check`).

## [1.1.2] - 2026-10-02

### Added
- npm/npx distribution wrapper and package metadata.

## [1.1.1] - 2026-09-29

### Changed
- **Breaking:** shell completion is disabled; running with no command shows help.

## [1.1.0] - 2026-09-28

### Added
- `calls:` / `raises:` annotations on function-like symbols.

### Changed
- **Breaking:** files renamed: `.omphalos_ignore` -> `.omphignore`, `.omphalos_index` -> `INDEX.md`.

## [1.0.0] - 2026-09-24

### Added
- First release as Omphalos: rebranded from the original indexer, with new CLI commands
  and options and expanded language support (Python, TypeScript/TSX, JavaScript, Go, Rust).

[Unreleased]: https://github.com/snui1s/Omphalos/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/snui1s/Omphalos/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/snui1s/Omphalos/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/snui1s/Omphalos/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/snui1s/Omphalos/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/snui1s/Omphalos/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/snui1s/Omphalos/releases/tag/v1.0.0
