// Repeat the reviewed controller suites without overwriting frozen evidence.
import {createHash} from "node:crypto";
import {spawn, spawnSync} from "node:child_process";
import {mkdir, mkdtemp, readFile, readdir, copyFile, writeFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";

const project = resolve(import.meta.dirname, "toy-project"), output = resolve(import.meta.dirname, "toy-output");
await mkdir(project); await mkdir(output);
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const sourceDigest = "toy-helper-extracted-from-bb331e5b4b477c6f5a625dca41f4e3525346c5d77982631bc7731aaa75f42d58";
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
  const processManagementErrors = [];
  const probe = () => {
    if (!child.pid) return false;
    try { return alive(child.pid); }
    catch (error) { processManagementErrors.push({operation: "probe", code: error.code, message: error.message}); return null; }
  };
  const send = signal => {
    if (!child.pid) return;
    try { signalGroup(child.pid, signal); }
    catch (error) { processManagementErrors.push({operation: signal, code: error.code, message: error.message}); }
  };
  const exited = new Promise(resolve => {
    child.once("exit", (code, signal) => { exitCode = code; exitSignal = signal; resolve(); });
    child.once("error", error => { spawnError = error.message; resolve(); });
  });
  const closed = new Promise(resolve => child.once("close", resolve));
  const timer = setTimeout(() => { timedOut = true; send("SIGTERM"); }, 300_000);
  const forceTimer = setTimeout(() => send("SIGKILL"), 305_000);
  let terminalTimer, directChildTerminal = false;
  await Promise.race([
    exited.then(() => { directChildTerminal = true; }),
    new Promise(resolve => { terminalTimer = setTimeout(() => { timedOut = true; resolve(); }, 310_000); }),
  ]);
  clearTimeout(terminalTimer);
  clearTimeout(timer); clearTimeout(forceTimer);
  const signals = [];
  // Retire owned descendants even if the direct test process exited first.
  for (const signal of ["SIGTERM", "SIGKILL"]) {
    if (probe() !== true) break;
    send(signal); signals.push(signal);
    const deadline = performance.now() + 5_000;
    while (probe() === true && performance.now() < deadline) await pause(25);
  }
  const terminalGroupState = probe();
  const processGroupEmpty = terminalGroupState === false && processManagementErrors.length === 0;
  // Wait for pipe EOF, not just the direct child's exit, before hashing output.
  let closeTimer, eofObserved = false, eofError = null;
  try {
    await Promise.race([closed, new Promise((_, reject) => {
      closeTimer = setTimeout(() => reject(new Error("owned_output_eof_timeout: " + name)), 5_000);
    })]);
    eofObserved = true;
  } catch (error) {
    eofError = error.message;
    // A failed EOF check must still retain the output already observed and a
    // command receipt. Preserve scratch while an unknown holder may remain.
    child.stdout.destroy(); child.stderr.destroy();
  } finally { clearTimeout(closeTimer); }
  const remainingTemporaryEntries = await readdir(scratch);
  const scratchRemoved = directChildTerminal && processGroupEmpty && eofObserved;
  if (scratchRemoved) await rm(scratch, {recursive: true});
  const out = Buffer.concat(stdout), err = Buffer.concat(stderr);
  await writeFile(join(directory, "stdout"), out);
  await writeFile(join(directory, "stderr"), err);
  const record = {name, argv: [process.execPath, ...args], cwd: project, started,
    finished: new Date().toISOString(), pid: child.pid ?? null, exitCode, exitSignal,
    timedOut, spawnError, signals, processGroupEmpty, sourceDigest, eofObserved, eofError,
    directChildTerminal, terminalGroupState, processManagementErrors,
    directChildUnrefOnFailure: !directChildTerminal,
    scratch, scratchRemoved, remainingTemporaryEntries,
    stdoutSHA256: hash(out), stderrSHA256: hash(err)};
  commands.push(record);
  await writeFile(join(directory, "command.json"), JSON.stringify(record, null, 2) + "\n");
  // Return the incomplete-cleanup receipt after the finite observation window;
  // an unconfirmed child must not silently keep this reporting process alive.
  if (!directChildTerminal) child.unref();
  console.log(JSON.stringify({name, exitCode, timedOut, processGroupEmpty}));
  if (exitCode !== 0 || timedOut || spawnError || !directChildTerminal || !processGroupEmpty || !eofObserved)
    throw new Error("controller_check_failed: " + name);
}

export {run,commands,project,output};
