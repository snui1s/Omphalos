# Codebase Symbol Index

## bin/omph.js
- const `{ spawnSync }` @3
- const `path` @4
- const `fs` @5
- const `args` @7
- const `isWin` @8
- function `run()` @10 (calls: `spawnSync`)
- function `hasCommand()` @22 (calls: `spawnSync`)
- function `findNativeBinary()` @36 (calls: `spawnSync`, `filter`, `map`, `res.stdout.split`, `l.trim`, `line.toLowerCase`, `lower.endsWith`, `lower.includes`)
- function `findVenvPython()` @67 (calls: `path.join`, `fs.existsSync`, `process.cwd`)
- function `main()` @79 (calls: `path.resolve`, `path.join`, `fs.existsSync`, `findNativeBinary`, `run`, `process.exit`, `findVenvPython`, `hasCommand`, `console.log`, `console.error`)

## src/omphalos/cache.py
- `calculate_sha256()` @15: Calculate the SHA-256 checksum of raw file bytes for change detection. (calls: `hexdigest`, `hashlib.sha256`)
- `load_cache()` @19: Load symbol cache from .omphcache. (calls: `cache_path.exists`, `json.loads`, `cache_path.read_text`, `isinstance`, `raw.get`)
- `save_cache()` @38: Save symbol cache to .omphcache atomically. (calls: `tempfile.mkstemp`, `os.fdopen`, `json.dump`, `os.replace`, `os.unlink`)

## src/omphalos/cli.py
- `_package_version()` @43: Read the installed package version (single source of truth: pyproject.toml). (calls: `version`)
- `_version_callback()` @51: Callback for --version flag to print the version and exit immediately. (calls: `typer.echo`, `typer.style`, `_package_version`; raises: `typer.Exit`)
- `main()` @63: Omphalos - Codebase symbol indexer for LLMs. (calls: `typer.echo`, `ctx.get_help`; raises: `typer.Exit`)
- `init()` @96: Create a default .omphignore file if not present in the target directory. (calls: `resolve`, `Path`, `ensure_ignore_file`, `typer.echo`, `typer.style`, `notify_if_update_available`, `_package_version`)
- `_execute_scan()` @112: Scan files, update index and cache, and return summary statistics. (calls: `load_ignore_spec`, `collect_git_files`, `collect_files`, `load_cache`, `as_posix`, `file_path.relative_to`, `file_path.read_bytes`, `typer.echo`, `typer.style`, `calculate_sha256`, `cache.get`, `cached.get`, `isinstance`, `extract_symbols`, `data.get`, `typer.progressbar`, `_process_file`, `renderer`, `index_path.write_text`, `save_cache`, `len`)
- `_start_watcher()` @175: Watch codebase files for changes and re-index automatically. (calls: `typer.echo`, `typer.style`, `str`, `time.strftime`, `rel_names.append`, `as_posix`, `p.relative_to`, `len`, `join`, `_execute_scan`, `watch_loop`)
- `scan()` @242: Scan multi-language codebase files and generate a symbol index with line numbers and docstrings. (calls: `resolve`, `Path`, `typer.echo`, `typer.style`, `join`, `ensure_ignore_file`, `load_ignore_spec`, `collect_git_files`, `collect_files`, `load_cache`, `typer.progressbar`, `as_posix`, `file_path.relative_to`, `file_path.read_bytes`, `calculate_sha256`, `cache.get`, `cached.get`, `isinstance`, `extract_symbols`, `renderer`, `index_path.read_text`, `index_path.exists`, `_execute_scan`, `notify_if_update_available`, `_package_version`, `_start_watcher`; raises: `typer.Exit`)
- `watch()` @362: Watch codebase files for changes and re-index automatically. (calls: `scan`)

## src/omphalos/ignore.py
- `ensure_ignore_file()` @60: Create a default .omphignore file if it does not already exist. (calls: `target.exists`, `target.write_text`, `IGNORE_TEMPLATE.strip`)
- `load_ignore_spec()` @73: Load and merge all ignore rules into a unified PathSpec. (calls: `list`, `ignore_file.exists`, `patterns.extend`, `splitlines`, `ignore_file.read_text`, `pathspec.GitIgnoreSpec.from_lines`)
- `collect_files()` @96: Recursively collect supported files, pruning directories matched by ignore spec. (calls: `os.walk`, `relative_to`, `Path`, `spec.match_file`, `as_posix`, `p.suffix.lower`, `target_files.append`, `target_files.sort`)
- class `NotAGitRepoError` @123
- `collect_git_files()` @127: Collect only files tracked by Git (via git ls-files), filtered by spec and extension. (calls: `subprocess.run`, `strip`, `proc.stderr.decode`, `proc.stdout.split`, `replace`, `chunk.decode`, `Path`, `p.suffix.lower`, `is_file`, `spec.match_file`, `target_files.append`, `target_files.sort`; raises: `NotAGitRepoError`)

## src/omphalos/parser.py
- `_text()` @41: Decode Tree-sitter AST node text bytes to a UTF-8 string. (calls: `decode`)
- `_mk_symbol()` @46: Create a standardized symbol schema dictionary.
- `_prev_comment_block()` @67: Return contiguous comment nodes immediately preceding the node (in top-to-bottom order). (calls: `len`, `text.rstrip`, `content_end_row`, `block.append`, `block.reverse`)
- `_get_py_docstring()` @88: Extract the first line of a Python function or class docstring, if present. (calls: `node.child_by_field_name`, `len`, `strip`, `_text`, `raw.splitlines`)
- `_go_doc()` @102: Go doc comment: first line of comment block attached above declaration (skipping //go: directives). (calls: `_prev_comment_block`, `strip`, `_text`, `t.startswith`, `t.removeprefix`)
- `_rust_doc()` @112: Rust doc comment: first line of /// comment block attached above an item. (calls: `_prev_comment_block`, `strip`, `_text`, `t.startswith`, `t.removeprefix`)
- `_ts_doc()` @123: JSDoc comment: first line containing content within a /** ... */ block attached above declaration. (calls: `_prev_comment_block`, `strip`, `_text`, `t.startswith`, `t.splitlines`, `removesuffix`, `removeprefix`, `raw.strip`)
- `_unwrap_decorated()` @136: Unwrap core definition node (function/class) from a Python decorated_definition.
- `_raise_target()` @157: Extract the exception type from a raise/throw statement. (calls: `first.child_by_field_name`, `_text`)
- `_is_simple_chain()` @176: True ถ้า node เป็นโซ่ identifier เรียบ ๆ เช่น `self`, `log`, `file_path.relative_to` (calls: `_is_simple_chain`)
- `_callee_name()` @192: Compact callee name: dotted chain เต็มถ้าต้นทางเรียบ, ไม่งั้นเหลือเฉพาะชื่อปลาย (calls: `len`, `_is_simple_chain`, `_text`)
- `_collect_logic()` @200: Collect deduplicated internal call targets and raised exception types of a function body. (calls: `_RAISE_NODES.get`, `stack.pop`, `_raise_target`, `raises.append`, `call_fields.get`, `n.child_by_field_name`, `_callee_name`, `calls.append`, `stack.extend`, `reversed`)
- `_annotate_logic()` @230: Attach `calls`/`raises` to function-like symbols (keys added only when non-empty). (calls: `node.child_by_field_name`, `_collect_logic`)
- `_extract_python()` @246: Extract all symbols from a Python AST (classes, methods, functions). (calls: `_unwrap_decorated`, `node.child_by_field_name`, `_text`, `_mk_symbol`, `_get_py_docstring`, `child.child_by_field_name`, `_annotate_logic`, `append`, `symbols.append`)
- `_ts_symbol()` @280: Extract a structured symbol dictionary from a TypeScript/JavaScript declaration node. (calls: `target.child_by_field_name`, `_mk_symbol`, `_text`, `_ts_doc`, `_annotate_logic`, `item.child_by_field_name`, `append`, `decl.child_by_field_name`)
- `_extract_ts_js()` @341: Extract symbols from TypeScript and JavaScript ASTs (functions, classes, interfaces, types, exports). (calls: `_ts_symbol`, `symbols.append`)
- `_extract_go()` @363: Extract symbols from Go AST (types, structs, interfaces, functions, methods with receivers). (calls: `spec.child_by_field_name`, `get`, `_text`, `_go_doc`, `len`, `symbols.append`, `_mk_symbol`, `node.child_by_field_name`, `_annotate_logic`)
- `_rust_vis()` @404: Extract visibility modifier string (e.g., 'pub') from a Rust item node. (calls: `_text`)
- `_extract_rust()` @412: Extract symbols from Rust AST (structs, enums, traits, functions, and impl blocks). (calls: `_rust_vis`, `node.child_by_field_name`, `_text`, `symbols.append`, `_mk_symbol`, `_rust_doc`, `_annotate_logic`, `item.child_by_field_name`, `append`)
- `extract_symbols()` @474: Parse file content using the appropriate Tree-sitter language grammar and extract code symbols. (calls: `file_path.suffix.lower`, `SUPPORTED_EXTENSIONS.get`, `file_path.read_bytes`, `str`, `_PARSER_PYTHON.parse`, `_extract_python`, `_PARSER_TS.parse`, `_extract_ts_js`, `_PARSER_TSX.parse`, `_PARSER_JS.parse`, `_PARSER_GO.parse`, `_extract_go`, `_PARSER_RUST.parse`, `_extract_rust`)

## src/omphalos/render.py
- `render_markdown()` @7: Render structured symbol data into Markdown format for LLM context or human reading. (calls: `files_data.items`, `data.get`, `lines.append`, `_render_md_symbols`, `join`)
- `_render_md_symbols()` @27: Recursively render symbols as nested Markdown bullet points. (calls: `sym.get`, `detail.append`, `join`, `lines.append`, `_render_md_symbols`)
- `render_json()` @51: Render structured symbol data into a JSON string for programmatic consumption. (calls: `data.get`, `files_data.items`, `json.dumps`)

## src/omphalos/updater.py
- `parse_version()` @16: Parse semver string into comparable tuple of ints. (calls: `lstrip`, `v.strip`, `re.findall`, `tuple`, `int`)
- `is_newer_version()` @23: Return True if latest is strictly newer than current version. (calls: `pkg_parse`, `parse_version`)
- `get_update_cache_path()` @32: Return user cache path for update checks. (calls: `Path.home`)
- `read_cached_version()` @38: Read last check timestamp and cached latest version. (calls: `cache_path.is_file`, `json.loads`, `cache_path.read_text`, `isinstance`, `float`, `raw.get`, `str`)
- `write_cached_version()` @53: Persist last check timestamp and latest version to cache file atomically. (calls: `cache_path.parent.mkdir`, `json.dumps`, `str`, `tempfile.mkstemp`, `os.fdopen`, `f.write`, `os.replace`, `os.path.exists`, `os.unlink`)
- `fetch_latest_pypi_version()` @76: Query PyPI JSON API for latest version string. (calls: `urllib.request.Request`, `urllib.request.urlopen`, `json.loads`, `decode`, `resp.read`, `data.get`, `info.get`, `str`)
- `check_for_update()` @92: Check if a newer version is available. (calls: `get_update_cache_path`, `time.time`, `read_cached_version`, `is_newer_version`, `fetch_latest_pypi_version`, `write_cached_version`)
- `format_update_notice()` @126: Generate a clean, styled CLI notice box for available updates. (calls: `max`, `len`, `typer.style`, `pad_styled`, `join`)
- `notify_if_update_available()` @167: Print update notification if a newer version is available and not suppressed. (calls: `os.environ.get`, `check_for_update`, `typer.echo`, `format_update_notice`)

## src/omphalos/watcher.py
- `snapshot_workspace()` @14: Take a timestamp/size snapshot of all tracked codebase and ignore files. (calls: `load_ignore_spec`, `collect_git_files`, `collect_files`, `p.stat`, `ign_path.exists`, `ign_path.stat`)
- `detect_changes()` @43: Return paths of added, modified, or deleted files between two snapshots. (calls: `curr.items`, `changed.append`)
- `watch_loop()` @57: Continuously poll workspace for changes and trigger on_change callback. (calls: `dict`, `snapshot_workspace`, `stop_check`, `time.sleep`, `detect_changes`, `on_change`)

## tests/fixtures/sample.go
- type `Account` (struct) @3
- type `BankService` (interface) @8
- func `OpenAccount()` @12
- func `(a *Account) Deposit()` @16

## tests/fixtures/sample.js
- export function `createCounter()` @2: Creates a counter closure.
- const `internalHelper()` @7

## tests/fixtures/sample.py
- `cached_fn()` @7: Compute something expensive.
- class `Greeter` @12: Greets people in various languages.
  - `greet()` @15: Return a greeting.
  - `fetch_greetings()` @19
- `top_level()` @23: ฟังก์ชันที่มีชื่อพารามิเตอร์เป็นภาษาไทย.

## tests/fixtures/sample.rs
- pub struct `DatabasePool` @1
- pub enum `DbError` @5
- pub fn `connect()` @10 (calls: `Ok`)
- impl `DatabasePool` @14
  - `pub fn get_connection()` @15
- impl `Drop for DatabasePool` @18
  - `fn drop()` @19

## tests/fixtures/sample.ts
- export interface `UserProfile` @1
- export type `AuthToken` @6
- export function `verifyToken()` @8
- export const `API_ENDPOINT` @12
- export const `logoutUser()` @14
- export class `SessionManager` @18
  - `createSession()` @19

## tests/fixtures/sample.tsx
- export interface `AvatarProps` @4: Props for the avatar component.
- export function `Avatar()` @10: Displays a user avatar.
- export const `AvatarList()` @14 (calls: `users.map`)

## tests/test_cache.py
- `test_sha256_known_value()` @10 (calls: `calculate_sha256`)
- `test_load_cache_missing_file()` @16 (calls: `load_cache`)
- `test_load_cache_corrupt_json()` @20 (calls: `write_text`, `load_cache`)
- `test_load_cache_old_version_is_discarded()` @25 (calls: `write_text`, `json.dumps`, `load_cache`)
- `test_load_cache_legacy_format_is_discarded()` @33 (calls: `write_text`, `json.dumps`, `load_cache`)
- `test_save_and_load_roundtrip()` @42 (calls: `save_cache`, `load_cache`, `json.loads`, `read_text`)
- `test_save_cache_is_atomic_on_failure()` @51 (calls: `save_cache`, `cache_path.read_text`, `pytest.raises`, `object`, `list`, `tmp_path.glob`)

## tests/test_cli.py
- `scan()` @35 (calls: `runner.invoke`, `str`)
- `test_scan_generates_index_and_cache()` @39 (calls: `write_text`, `scan`, `read_text`, `json.loads`)
- `test_scan_reuses_cache_without_reparsing()` @58 (calls: `write_text`, `scan`, `json.loads`, `cache_path.read_text`, `cache_path.write_text`, `json.dumps`, `monkeypatch.setattr`, `read_text`; raises: `AssertionError`)
- `test_scan_no_cache_ignores_poisoned_cache()` @79 (calls: `write_text`, `scan`, `json.loads`, `cache_path.read_text`, `cache_path.write_text`, `json.dumps`, `read_text`)
- `test_scan_corrupt_cache_entry_falls_back_to_reparse()` @95 (calls: `write_text`, `scan`, `json.loads`, `cache_path.read_text`, `cache_path.write_text`, `json.dumps`, `read_text`)
- `test_scan_reports_parse_errors()` @110 (calls: `write_text`, `monkeypatch.setattr`, `echoed.append`, `str`, `scan`, `any`, `exists`)
- `test_scan_no_failure_summary_when_all_ok()` @130 (calls: `write_text`, `monkeypatch.setattr`, `echoed.append`, `str`, `scan`, `any`)
- `test_scan_json_format()` @142 (calls: `write_text`, `scan`, `json.loads`, `read_text`, `next`)
- `test_scan_rejects_invalid_format()` @159 (calls: `scan`)
- `test_scan_output_to_custom_path()` @164 (calls: `write_text`, `out.parent.mkdir`, `scan`, `str`, `out.read_text`, `exists`)
- `test_check_passes_when_fresh()` @174 (calls: `write_text`, `scan`)
- `test_check_fails_when_stale_and_writes_nothing()` @182 (calls: `write_text`, `scan`, `read_text`)
- `test_check_fails_when_index_missing()` @195 (calls: `write_text`, `scan`)
- `test_version_flag()` @201 (calls: `runner.invoke`)
- `test_no_args_shows_help()` @207 (calls: `runner.invoke`)
- `test_git_only_scans_only_tracked_files()` @219 (calls: `subprocess.run`, `write_text`, `scan`, `read_text`)
- `test_git_only_outside_repo_fails()` @233 (calls: `scan`, `result.output.lower`)
- `test_scan_watch_rejects_check_flag()` @239 (calls: `scan`)
- `test_watch_command_runs_initial_scan()` @245 (calls: `write_text`, `called.append`, `monkeypatch.setattr`, `runner.invoke`, `str`, `exists`, `len`)
- `test_watch_reindexes_on_change()` @261 (calls: `foo_py.write_text`, `on_change`, `monkeypatch.setattr`, `scan`, `read_text`)
- `test_scan_short_w_flag()` @278 (calls: `monkeypatch.setattr`, `called.append`, `scan`, `len`)
- `test_watch_keyboard_interrupt_handled_cleanly()` @287 (calls: `monkeypatch.setattr`, `runner.invoke`, `str`; raises: `KeyboardInterrupt`)
- `test_watch_formats_multiple_changed_files()` @298 (calls: `f1.write_text`, `f2.write_text`, `on_change`, `range`, `fi.write_text`, `files.append`, `monkeypatch.setattr`, `runner.invoke`, `str`)
- `test_watch_reports_parse_error_on_change()` @322 (calls: `bad_py.write_text`, `monkeypatch.setattr`, `on_change`, `runner.invoke`, `str`)
- `test_watch_format_json_and_custom_output()` @342 (calls: `custom_out.parent.mkdir`, `write_text`, `monkeypatch.setattr`, `runner.invoke`, `str`, `custom_out.exists`, `json.loads`, `custom_out.read_text`)

## tests/test_edge_cases.py
- `by_name()` @16 (calls: `by_name`, `s.get`)
- `test_bom_prefix_does_not_shift_line_numbers()` @28 (calls: `extract_symbols`, `Path`)
- `test_binary_garbage_with_supported_extension()` @34 (calls: `extract_symbols`, `Path`, `bytes`, `range`, `r.get`)
- `test_null_bytes_inside_file()` @40 (calls: `extract_symbols`, `Path`, `r.get`, `isinstance`)
- `test_crlf_line_endings_keep_line_numbers()` @46 (calls: `extract_symbols`, `Path`)
- `test_thai_identifiers_and_docstrings()` @54 (calls: `encode`, `extract_symbols`, `Path`)
- `test_large_file_parses_correctly()` @66 (calls: `join`, `encode`, `range`, `extract_symbols`, `Path`, `len`)
- `test_comment_only_file()` @75 (calls: `extract_symbols`, `Path`)
- `test_file_with_only_blank_lines()` @80 (calls: `extract_symbols`, `Path`)
- `test_jsx_uses_tsx_parser_with_jsx_syntax()` @86 (calls: `extract_symbols`, `Path`)
- `test_mjs_and_cjs_map_to_javascript()` @94 (calls: `extract_symbols`, `Path`)
- `test_fixture_sample_python()` @102 (calls: `extract_symbols`, `by_name`)
- `test_fixture_sample_tsx()` @117 (calls: `extract_symbols`, `by_name`)
- `test_fixture_sample_js()` @133 (calls: `extract_symbols`, `by_name`)
- `test_scan_unicode_and_spaces_in_filename()` @146 (calls: `write_text`, `runner.invoke`, `str`, `read_text`, `json.loads`)
- `test_scan_directory_with_no_supported_files()` @158 (calls: `write_text`, `runner.invoke`, `str`, `read_text`, `index.startswith`)
- `test_scan_deeply_nested_files()` @169 (calls: `range`, `deep.mkdir`, `write_text`, `runner.invoke`, `str`, `join`, `read_text`)

## tests/test_ignore.py
- `make_tree()` @20 (calls: `p.parent.mkdir`, `p.write_text`)
- `collected_rel()` @27 (calls: `collect_files`, `as_posix`, `f.relative_to`)
- `test_ensure_ignore_file_creates_when_missing()` @32 (calls: `ensure_ignore_file`, `created.exists`)
- `test_ensure_ignore_file_respects_existing()` @39 (calls: `write_text`, `ensure_ignore_file`)
- `test_collect_files_skips_ignored_dirs_and_extensions()` @44 (calls: `make_tree`, `load_ignore_spec`, `collected_rel`)
- `test_negation_can_reinclude_directory()` @51 (calls: `make_tree`, `write_text`, `load_ignore_spec`, `collected_rel`)
- `test_negation_inside_excluded_dir_does_not_apply()` @58 (calls: `make_tree`, `write_text`, `load_ignore_spec`, `collected_rel`)
- `test_omphignore_overrides_gitignore()` @66 (calls: `make_tree`, `write_text`, `load_ignore_spec`, `collected_rel`)
- `test_collect_files_is_sorted()` @74 (calls: `p.parent.mkdir`, `p.write_text`, `load_ignore_spec`, `collect_files`, `sorted`)
- `init_git_repo()` @87 (calls: `subprocess.run`, `mkdir`, `write_text`)
- `test_collect_git_files_only_tracked()` @99 (calls: `init_git_repo`, `load_ignore_spec`, `collect_git_files`, `as_posix`, `f.relative_to`)
- `test_collect_git_files_outside_repo_raises()` @108 (calls: `load_ignore_spec`, `pytest.raises`, `collect_git_files`)

## tests/test_logic.py
- `by_name()` @14 (calls: `by_name`, `s.get`)
- `test_python_calls_and_raises()` @26 (calls: `extract_symbols`, `Path`)
- `test_python_plain_function_has_no_logic_keys()` @44 (calls: `extract_symbols`, `Path`)
- `test_python_method_inside_class()` @50 (calls: `by_name`, `extract_symbols`, `Path`)
- `test_python_signature_and_decorator_calls_excluded()` @63 (calls: `by_name`, `extract_symbols`, `Path`, `set`)
- `test_ts_function_calls_and_throws()` @80 (calls: `extract_symbols`, `Path`)
- `test_ts_arrow_function_constant()` @97 (calls: `extract_symbols`, `Path`)
- `test_go_calls_only_no_raises_semantics()` @106 (calls: `by_name`, `extract_symbols`, `Path`)
- `test_rust_fn_calls()` @123 (calls: `extract_symbols`, `Path`)
- `test_rust_impl_method_calls()` @136 (calls: `by_name`, `extract_symbols`, `Path`)
- `test_markdown_renders_logic_inline()` @150 (calls: `render_markdown`)
- `test_markdown_omits_logic_when_empty()` @163 (calls: `render_markdown`)
- `test_json_passes_logic_through()` @174 (calls: `write_text`, `runner.invoke`, `str`, `json.loads`, `out.read_text`)
- `test_cli_scan_end_to_end_includes_logic()` @187 (calls: `write_text`, `runner.invoke`, `str`, `read_text`, `json.loads`)

## tests/test_parser.py
- `by_name()` @7 (calls: `by_name`, `s.get`)
- `test_extract_python_structured()` @17 (calls: `Path`, `extract_symbols`, `len`)
- `test_extract_python_decorated_uses_def_line()` @47 (calls: `Path`, `extract_symbols`)
- `test_extract_go_docs_and_lines()` @58 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_go_interface_and_plain_type()` @91 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_rust_docs_and_traits()` @105 (calls: `Path`, `extract_symbols`, `by_name`, `next`)
- `test_extract_rust_trait()` @151 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_ts_jsdoc_and_exports()` @161 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_ts_multiline_jsdoc_takes_first_line()` @204 (calls: `Path`, `extract_symbols`)
- `test_extract_symbols_reads_file_when_no_content()` @218 (calls: `p.write_text`, `extract_symbols`, `by_name`)
- `test_extract_symbols_empty_content()` @225 (calls: `extract_symbols`)
- `test_extract_symbols_unknown_extension()` @229 (calls: `extract_symbols`)
- `test_extract_fixture_ts()` @233 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_fixture_go()` @242 (calls: `Path`, `extract_symbols`, `by_name`)
- `test_extract_fixture_rust()` @249 (calls: `Path`, `extract_symbols`, `by_name`, `any`)

## tests/test_updater.py
- `test_parse_version()` @21 (calls: `parse_version`)
- `test_is_newer_version()` @28 (calls: `is_newer_version`)
- `test_cache_read_write()` @36 (calls: `read_cached_version`, `cache_file.write_text`, `write_cached_version`)
- `test_check_for_update_cached_within_ttl()` @56 (calls: `time.time`, `write_cached_version`, `monkeypatch.setattr`, `pytest.fail`, `check_for_update`)
- `test_check_for_update_fetches_when_expired()` @73 (calls: `time.time`, `write_cached_version`, `monkeypatch.setattr`, `check_for_update`, `read_cached_version`)
- `test_check_for_update_handles_network_failure()` @90 (calls: `monkeypatch.setattr`, `check_for_update`)
- `test_fetch_latest_pypi_version_success()` @99 (calls: `MagicMock`, `encode`, `json.dumps`, `monkeypatch.setattr`, `fetch_latest_pypi_version`)
- `test_fetch_latest_pypi_version_network_error()` @109 (calls: `monkeypatch.setattr`, `fetch_latest_pypi_version`; raises: `OSError`)
- `test_format_update_notice()` @117 (calls: `format_update_notice`)
- `test_notify_suppressed_in_ci()` @125 (calls: `monkeypatch.setenv`, `monkeypatch.setattr`, `echoed.append`, `notify_if_update_available`, `len`)
- `test_notify_suppressed_in_json_and_check()` @133 (calls: `monkeypatch.delenv`, `monkeypatch.setattr`, `echoed.append`, `notify_if_update_available`, `len`)
- `test_notify_prints_when_update_available()` @142 (calls: `monkeypatch.delenv`, `write_cached_version`, `time.time`, `monkeypatch.setattr`, `echoed.append`, `notify_if_update_available`, `len`)

## tests/test_watcher.py
- `test_snapshot_workspace_and_detect_changes()` @15 (calls: `py_file.write_text`, `write_text`, `snapshot_workspace`, `detect_changes`, `ts_file.write_text`, `ts_file.unlink`)
- `test_snapshot_workspace_tracks_ignore_files()` @45 (calls: `omphignore.write_text`, `gitignore.write_text`, `snapshot_workspace`, `time.sleep`, `detect_changes`)
- `test_snapshot_workspace_git_only()` @64 (calls: `subprocess.run`, `tracked_py.write_text`, `untracked_py.write_text`, `snapshot_workspace`)
- `test_watch_loop_invokes_on_change_with_initial_snapshot()` @80 (calls: `py_file.write_text`, `snapshot_workspace`, `invoked_changes.append`, `list`, `watch_loop`, `len`)
- `test_watch_loop_with_background_thread_and_stop_check()` @106 (calls: `py_file.write_text`, `invoked_changes.append`, `list`, `time.sleep`, `threading.Thread`, `t.start`, `watch_loop`, `t.join`, `len`)
- `test_watch_loop_debounce_aggregates_rapid_changes()` @139 (calls: `file1.write_text`, `file2.write_text`, `snapshot_workspace`, `invoked.append`, `list`, `watch_loop`, `len`)
- `test_watch_loop_exits_on_not_a_git_repo()` @171 (calls: `watch_loop`, `called.append`, `len`)
