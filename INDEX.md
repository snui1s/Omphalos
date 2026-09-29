# Codebase Symbol Index

## src/omphalos/cache.py
- `calculate_sha256()` @15: Calculate the SHA-256 checksum of raw file bytes for change detection. (calls: `hexdigest`, `hashlib.sha256`)
- `load_cache()` @19: Load symbol cache from .omphcache. (calls: `cache_path.exists`, `json.loads`, `cache_path.read_text`, `isinstance`, `raw.get`)
- `save_cache()` @38: Save symbol cache to .omphcache atomically. (calls: `tempfile.mkstemp`, `os.fdopen`, `json.dump`, `os.replace`, `os.unlink`)

## src/omphalos/cli.py
- `_package_version()` @26: Read the installed package version (single source of truth: pyproject.toml). (calls: `version`)
- `_version_callback()` @34: Callback for --version flag to print the version and exit immediately. (calls: `typer.echo`, `_package_version`; raises: `typer.Exit`)
- `main()` @42: Omphalos - Codebase symbol indexer for LLMs. (calls: `typer.echo`, `ctx.get_help`; raises: `typer.Exit`)
- `init()` @56: Create a default .omphignore file if not present in the target directory. (calls: `resolve`, `Path`, `ensure_ignore_file`, `typer.echo`)
- `scan()` @69: Scan multi-language codebase files and generate a symbol index with line numbers and docstrings. (calls: `resolve`, `Path`, `typer.echo`, `join`, `ensure_ignore_file`, `load_ignore_spec`, `collect_git_files`, `collect_files`, `load_cache`, `typer.progressbar`, `as_posix`, `file_path.relative_to`, `file_path.read_bytes`, `calculate_sha256`, `cache.get`, `cached.get`, `isinstance`, `extract_symbols`, `data.get`, `renderer`, `index_path.read_text`, `index_path.exists`, `index_path.write_text`, `save_cache`, `len`; raises: `typer.Exit`)

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
