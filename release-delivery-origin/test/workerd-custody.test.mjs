import assert from "node:assert/strict";
import {spawn, spawnSync} from "node:child_process";
import {mkdtemp, readFile, rm, stat, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import test from "node:test";
import {absent, removeReplayScratch, WorkerdCustody} from "./workerd-custody.mjs";

const cases = [
  {name: "unexpected readiness child preserves scratch after direct and group exit", childPhase: "ready"},
  {name: "unexpected pre-disposal child preserves scratch after direct and group exit", childPhase: "beforeDispose"},
  {name: "unverified readiness preserves scratch after direct and group exit", readinessFailed: true},
  {name: "denied group observation preserves scratch after direct exit", probeDenied: true},
  {name: "terminal workerd custody removes scratch", terminal: true},
];

for (const {name, childPhase, readinessFailed, probeDenied, terminal} of cases) {
  test(name, async () => {
    const scratch = await mkdtemp(join(tmpdir(), "mixer-w11-inert-custody-"));
    const marker = join(scratch, "marker");
    const custody = new WorkerdCustody();
    let child;
    try {
      await writeFile(marker, "fixture");
      child = custody.capture(spawn, process.execPath, ["-e", "process.stdin.resume()"],
        {stdio: ["pipe", "ignore", "ignore"]});
      const pid = child.pid;
      const group = spawnSync("/bin/ps", ["-o", "pgid=", "-p", String(pid)],
        {encoding: "utf8", timeout: 1000, maxBuffer: 1024});
      assert.equal(group.status, 0, "observe the exact inert child");
      assert.equal(Number(group.stdout.trim()), pid);
      const inertChildren = Array.from({length: 12}, (_, i) => ({pid: 100_001 + i, parentPid: pid}));

      if (!readinessFailed) {
        for (const phase of ["ready", "beforeDispose"]) {
          const observe = () => custody.observe(phase,
            () => ({pid, processes: childPhase === phase ? inertChildren : []}));
          if (childPhase === phase) {
            assert.throws(observe, /unexpected workerd child/);
            break;
          }
          assert.equal(observe(), pid);
        }
      }

      const close = custody.close(async () => { child.stdin.end(); }, id => {
        if (probeDenied && id === -pid) throw Object.assign(new Error("group probe denied"), {code: "EPERM"});
        return absent(id);
      });
      if (probeDenied) await assert.rejects(close, {code: "EPERM"});
      else await close;
      assert.deepEqual(custody.receipt.close, {code: 0, signal: null});
      assert.equal(custody.receipt.exactPidAbsent, true);
      assert.equal(custody.receipt.groupAbsent, !probeDenied);
      if (childPhase) {
        assert.equal(custody.receipt[childPhase], "unexpected_child");
        assert.deepEqual(custody.receipt.unexpectedChildren,
          {count: 12, pids: inertChildren.slice(0, 8).map(row => row.pid)});
      }

      if (terminal) {
        await removeReplayScratch(scratch, custody);
        await assert.rejects(stat(scratch), {code: "ENOENT"});
      } else {
        await assert.rejects(removeReplayScratch(scratch, custody), /unresolved workerd custody/);
        assert.equal(await readFile(marker, "utf8"), "fixture");
      }
    } finally {
      if (child && !child.stdin.writableEnded) {
        await custody.close(async () => { child.stdin.end(); });
      }
      // Only this inert fixture is removed here. The reported child rows are synthetic.
      await rm(scratch, {recursive: true, force: true});
    }
  });
}
