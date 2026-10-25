// Repeat the reviewed controller suites without overwriting frozen evidence.
import {createHash} from "node:crypto";
import {spawn, spawnSync} from "node:child_process";
import {mkdir, mkdtemp, readFile, readdir, copyFile, writeFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";

const project = resolve(import.meta.dirname, "toy-project"), output = resolve(import.meta.dirname, "toy-output");
await mkdir(project); await mkdir(output);
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const sourceDigest = "toy-helper-extracted-from-2bf5bf923a5b97717cc96335d06c2b8d8aebd1be4a5a7ae2da2a3d392e26ba0f";
const commands = [];
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function alive(pid) {
  try { process.kill(-pid, 0); return true; }
  catch (error) { if (error.code === "ESRCH") return false; throw error; }
}
function signalGroup(pid, signal) {
  try { process.kill(-pid, signal); }
  catch (error) { if (error.code !== "ESRCH") throw error; }
}
async function run(name, args, extraEnv = {}) {
  const directory = join(output, name);
  await mkdir(directory);
  const scratch = join(directory, "scratch");
  await mkdir(scratch);
  const stdout = [], stderr = [], started = new Date().toISOString();
  const child = spawn(process.execPath, args, {
    cwd: project, detached: true, stdio: ["ignore", "pipe", "pipe"],
    env: {...process.env, ...extraEnv, TMPDIR: scratch, TMP: scratch, TEMP: scratch},
  });
  child.stdout.on("data", bytes => stdout.push(bytes));
  child.stderr.on("data", bytes => stderr.push(bytes));
  let exitCode = null, exitSignal = null, timedOut = false, spawnError = null;
  const exited = new Promise(resolve => {
    child.once("exit", (code, signal) => { exitCode = code; exitSignal = signal; resolve(); });
    child.once("error", error => { spawnError = error.message; resolve(); });
  });
  const closed = new Promise(resolve => child.once("close", resolve));
  const timer = setTimeout(() => { timedOut = true; if (child.pid) signalGroup(child.pid, "SIGTERM"); }, 300_000);
  const forceTimer = setTimeout(() => { if (child.pid) signalGroup(child.pid, "SIGKILL"); }, 305_000);
  await exited;
  clearTimeout(timer); clearTimeout(forceTimer);
  const signals = [];
  // Retire owned descendants even if the direct test process exited first.
  for (const signal of ["SIGTERM", "SIGKILL"]) {
    if (!child.pid || !alive(child.pid)) break;
    signalGroup(child.pid, signal); signals.push(signal);
    const deadline = Date.now() + 5_000;
    while (alive(child.pid) && Date.now() < deadline) await pause(25);
  }
  const processGroupEmpty = !child.pid || !alive(child.pid);
  // Wait for pipe EOF, not just the direct child's exit, before hashing output.
  let closeTimer;
  try {
    await Promise.race([closed, new Promise((_, reject) => {
      closeTimer = setTimeout(() => reject(new Error("owned_output_eof_timeout: " + name)), 5_000);
    })]);
  } finally { clearTimeout(closeTimer); }
  const remainingTemporaryEntries = await readdir(scratch);
  if (processGroupEmpty) await rm(scratch, {recursive: true});
  const out = Buffer.concat(stdout), err = Buffer.concat(stderr);
  await writeFile(join(directory, "stdout"), out);
  await writeFile(join(directory, "stderr"), err);
  const record = {name, argv: [process.execPath, ...args], cwd: project, started,
    finished: new Date().toISOString(), pid: child.pid ?? null, exitCode, exitSignal,
    timedOut, spawnError, signals, processGroupEmpty, sourceDigest,
    scratch, scratchRemoved: processGroupEmpty, remainingTemporaryEntries,
    stdoutSHA256: hash(out), stderrSHA256: hash(err)};
  commands.push(record);
  await writeFile(join(directory, "command.json"), JSON.stringify(record, null, 2) + "\n");
  console.log(JSON.stringify({name, exitCode, timedOut, processGroupEmpty}));
  if (exitCode !== 0 || timedOut || spawnError || !processGroupEmpty)
    throw new Error("controller_check_failed: " + name);
}

export {run,commands,project,output};
