import assert from "node:assert/strict";
import {rm, stat} from "node:fs/promises";
import {setTimeout as delay} from "node:timers/promises";

export function absent(pid) {
  try {
    process.kill(pid, 0);
    return false;
  } catch (error) {
    if (error.code === "ESRCH") return true;
    throw error;
  }
}

export async function until(predicate, limitMs) {
  const deadline = Date.now() + limitMs;
  do {
    if (await predicate()) return;
    await delay(50);
  } while (Date.now() < deadline);
  throw new Error("observation_deadline");
}

export function deadline(promise, milliseconds, name) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(name + "_deadline")), milliseconds);
    promise.then(resolve, reject).finally(() => clearTimeout(timer));
  });
}

export class WorkerdCustody {
  #facts = {
    launchAttempts: 0, pid: null, pgid: null, ready: "unobserved", beforeDispose: "unobserved",
    unexpectedChildren: null, disposed: false, close: null, exactPidAbsent: false, groupAbsent: false,
  };
  #closed;

  capture(spawn, program, args, options) {
    const first = ++this.#facts.launchAttempts === 1;
    // On POSIX a detached child starts a new process group with PGID equal to its PID.
    const child = spawn(program, args, {...options, detached: true});
    if (first) {
      this.#facts.pid = child.pid ?? null;
      this.#facts.pgid = this.#facts.pid;
      this.#closed = new Promise(resolve => child.once("close", (code, signal) => {
        this.#facts.close = {code, signal};
        resolve();
      }));
    }
    return child;
  }

  observe(phase, inspect) {
    this.#facts[phase] = "unverified";
    const {pid, processes} = inspect();
    assert(this.#facts.launchAttempts === 1 && pid === this.#facts.pid,
      "workerd identity unavailable");

    const children = processes.filter(row => row.parentPid === pid);
    if (children.length > 0) {
      this.#facts[phase] = "unexpected_child";
      this.#facts.unexpectedChildren ??= {count: children.length, pids: children.slice(0, 8).map(row => row.pid)};
      throw new Error("unexpected workerd child");
    }
    this.#facts[phase] = "verified";
    return pid;
  }

  async close(dispose, probeAbsent = absent) {
    if (dispose) {
      await deadline(dispose(), 8000, "workerd_dispose");
      this.#facts.disposed = true;
    }
    const {pid, pgid} = this.#facts;
    if (pid === null) return;
    await deadline(this.#closed, 2500, "workerd_close");
    await until(() => {
      this.#facts.exactPidAbsent = probeAbsent(pid);
      this.#facts.groupAbsent = probeAbsent(-pgid);
      return this.#facts.exactPidAbsent && this.#facts.groupAbsent;
    }, 2500);
  }

  get receipt() {
    return this.#facts;
  }

  assertTerminal() {
    const facts = this.#facts;
    // An observed child could have escaped the group before the group probe.
    assert(facts.launchAttempts === 1 && facts.ready === "verified" &&
      facts.beforeDispose === "verified" && facts.unexpectedChildren === null &&
      facts.disposed && facts.close && facts.exactPidAbsent && facts.groupAbsent,
      "unresolved workerd custody");
  }
}

export async function removeReplayScratch(scratch, workerd) {
  workerd?.assertTerminal();
  await rm(scratch, {recursive: true});
  await assert.rejects(stat(scratch), {code: "ENOENT"});
}
