# Agent Guidelines

## Codebase Navigation & Exploration

Before searching, running grep, or opening entire source files across the codebase:

1. **Always read [`INDEX.md`](INDEX.md) first.** It provides an instant symbol map of the entire repository with exact line numbers.
2. Use the symbols, line locations (`@<line>`), and internal logic hints (`calls:`, `raises:`) in [`INDEX.md`](INDEX.md) to pinpoint definitions directly.
3. Inspect or slice-read only the specific line ranges or files needed for the task, rather than loading entire files into context.
