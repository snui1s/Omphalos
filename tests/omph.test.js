const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const WRAPPER = path.resolve(__dirname, "..", "bin", "omph.js");
const { isWrapperPath, pickNativeBinary, findVenvPython } = require(WRAPPER);

const isWin = process.platform === "win32";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "omph-test-"));
}

test("isWrapperPath rejects npm shims and scripts", () => {
  assert.ok(isWrapperPath("C:\\Users\\me\\AppData\\Roaming\\npm\\omph"));
  assert.ok(isWrapperPath("C:\\Users\\me\\AppData\\Roaming\\npm\\omph.cmd"));
  assert.ok(isWrapperPath("C:\\Users\\me\\AppData\\Roaming\\npm\\omph.ps1"));
  assert.ok(isWrapperPath("/usr/lib/node_modules/omphalos/bin/omph"));
  assert.ok(isWrapperPath("/some/where/omph.js"));
});

test("isWrapperPath does not reject paths that merely contain 'npm'", () => {
  assert.ok(!isWrapperPath("C:\\Users\\npmfan\\.local\\bin\\omph.exe"));
  assert.ok(!isWrapperPath("/home/npmuser/.local/bin/omph"));
});

test("isWrapperPath rejects a symlink that resolves to the wrapper itself", { skip: isWin }, () => {
  const dir = tmpDir();
  try {
    const link = path.join(dir, "omph");
    fs.symlinkSync(WRAPPER, link);
    assert.ok(isWrapperPath(link, WRAPPER));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("pickNativeBinary skips wrappers and returns first native binary", () => {
  const lines = [
    "C:\\Users\\me\\AppData\\Roaming\\npm\\omph",
    "C:\\Users\\me\\AppData\\Roaming\\npm\\omph.cmd",
    "C:\\Users\\me\\.local\\bin\\omph.exe",
    "C:\\other\\omph.exe",
  ];
  assert.strictEqual(pickNativeBinary(lines), "C:\\Users\\me\\.local\\bin\\omph.exe");
});

test("pickNativeBinary returns null when only wrappers exist", () => {
  assert.strictEqual(pickNativeBinary(["/usr/lib/node_modules/omphalos/bin/omph.js"]), null);
  assert.strictEqual(pickNativeBinary([]), null);
});

test("findVenvPython honours VIRTUAL_ENV", () => {
  const dir = tmpDir();
  const saved = process.env.VIRTUAL_ENV;
  try {
    const py = path.join(dir, isWin ? "Scripts/python.exe" : "bin/python");
    fs.mkdirSync(path.dirname(py), { recursive: true });
    fs.writeFileSync(py, "");
    process.env.VIRTUAL_ENV = dir;
    assert.strictEqual(findVenvPython(), py);
  } finally {
    if (saved === undefined) delete process.env.VIRTUAL_ENV;
    else process.env.VIRTUAL_ENV = saved;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("findVenvPython returns null when no venv exists", () => {
  const dir = tmpDir();
  const savedEnv = process.env.VIRTUAL_ENV;
  const savedCwd = process.cwd();
  try {
    delete process.env.VIRTUAL_ENV;
    process.chdir(dir);
    assert.strictEqual(findVenvPython(), null);
  } finally {
    process.chdir(savedCwd);
    if (savedEnv !== undefined) process.env.VIRTUAL_ENV = savedEnv;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("wrapper prints install guidance and exits 1 when nothing can launch Omphalos", () => {
  const dir = tmpDir();
  try {
    const env = { PATH: "" };
    if (isWin) env.SystemRoot = process.env.SystemRoot;
    const res = spawnSync(process.execPath, [WRAPPER, "--help"], {
      cwd: dir,
      env,
      encoding: "utf-8",
    });
    assert.strictEqual(res.status, 1);
    assert.match(res.stderr, /Could not launch Omphalos/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
