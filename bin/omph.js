#!/usr/bin/env node

const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const args = process.argv.slice(2);
const isWin = process.platform === "win32";

function run(cmd, cmdArgs, extraEnv = {}) {
  const result = spawnSync(cmd, cmdArgs, {
    stdio: "inherit",
    shell: isWin,
    env: { ...process.env, ...extraEnv },
  });
  if (result.error) {
    return { ok: false, error: result.error, status: 1 };
  }
  return { ok: true, status: result.status ?? 0 };
}

function hasCommand(cmd, testArgs = ["--version"], extraEnv = {}) {
  try {
    const res = spawnSync(cmd, testArgs, {
      stdio: "ignore",
      shell: isWin,
      env: { ...process.env, ...extraEnv },
    });
    return res.status === 0;
  } catch {
    return false;
  }
}

// Find native Python/compiled executable in PATH, excluding npm wrapper scripts to prevent recursion
function findNativeBinary(binName) {
  try {
    const lookupCmd = isWin ? "where.exe" : "which";
    const lookupArgs = isWin ? [binName] : ["-a", binName];
    const res = spawnSync(lookupCmd, lookupArgs, {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "ignore"],
      shell: isWin,
    });
    if (res.status !== 0 || !res.stdout) return null;
    const lines = res.stdout.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    for (const line of lines) {
      const lower = line.toLowerCase();
      // Skip npm shims, node wrappers, cmd/ps1 scripts, and node_modules
      if (
        lower.endsWith(".js") ||
        lower.endsWith(".cmd") ||
        lower.endsWith(".ps1") ||
        lower.includes("npm") ||
        lower.includes("node_modules")
      ) {
        continue;
      }
      return line;
    }
  } catch {
    return null;
  }
  return null;
}

function findVenvPython() {
  const venvDir = process.env.VIRTUAL_ENV;
  if (venvDir) {
    const py = path.join(venvDir, isWin ? "Scripts/python.exe" : "bin/python");
    if (fs.existsSync(py)) return py;
  }
  // Check local .venv in cwd
  const localVenvPy = path.join(process.cwd(), ".venv", isWin ? "Scripts/python.exe" : "bin/python");
  if (fs.existsSync(localVenvPy)) return localVenvPy;
  return null;
}

function main() {
  const repoSrc = path.resolve(__dirname, "..", "src");
  const localCli = path.join(repoSrc, "omphalos", "cli.py");
  const extraEnv = fs.existsSync(localCli) ? { PYTHONPATH: repoSrc } : {};

  // 1. Look for native Python/binary CLI executable (e.g. omph.exe installed by pip/uv)
  // Strictly ignores npm/node wrapper scripts to prevent recursive infinite loops
  const nativeOmph = findNativeBinary("omph") || findNativeBinary("omphalos");
  if (nativeOmph) {
    const res = run(nativeOmph, args);
    if (res.ok) process.exit(res.status);
  }

  // 2. Check active or local .venv Python
  const venvPy = findVenvPython();
  if (venvPy && hasCommand(venvPy, ["-c", "import omphalos"], extraEnv)) {
    const res = run(venvPy, ["-m", "omphalos.cli", ...args], extraEnv);
    if (res.ok) process.exit(res.status);
  }

  // 3. Try python / python3 / py in system PATH if omphalos module is already installed
  const pyCandidates = isWin ? ["python", "py", "python3"] : ["python3", "python"];
  for (const py of pyCandidates) {
    if (hasCommand(py, ["-c", "import omphalos"], extraEnv)) {
      const res = run(py, ["-m", "omphalos.cli", ...args], extraEnv);
      if (res.ok) process.exit(res.status);
    }
  }

  // 4. Try uvx if available (runs on-demand without manual Python install)
  if (hasCommand("uvx")) {
    const res = run("uvx", ["omphalos", ...args]);
    if (res.ok) process.exit(res.status);
  }

  // 5. Try uv run if available
  if (hasCommand("uv")) {
    const res = run("uv", ["run", "--with", "omphalos", "omph", ...args]);
    if (res.ok) process.exit(res.status);
  }

  // 6. Try pipx if available
  if (hasCommand("pipx")) {
    const res = run("pipx", ["run", "omphalos", ...args]);
    if (res.ok) process.exit(res.status);
  }

  // 7. If Python is installed but omphalos is not yet installed, auto-install via pip
  for (const py of pyCandidates) {
    if (hasCommand(py, ["--version"])) {
      console.log("\n[omphalos] Python detected. Automatically installing 'omphalos' package via pip...");
      const installRes = run(py, ["-m", "pip", "install", "omphalos"]);
      if (installRes.ok && installRes.status === 0) {
        if (hasCommand(py, ["-c", "import omphalos"])) {
          const res = run(py, ["-m", "omphalos.cli", ...args]);
          if (res.ok) process.exit(res.status);
        }
      }
    }
  }

  // 8. Fallback: actionable guidance
  console.error("\n[omphalos] Could not launch Omphalos.");
  console.error("Omphalos requires Python (>=3.10) or uv:");
  console.error("  Option 1 (Recommended): Install via uv");
  console.error("    $ uv tool install omphalos");
  console.error("  Option 2: Install via pip");
  console.error("    $ pip install omphalos\n");
  process.exit(1);
}

main();
