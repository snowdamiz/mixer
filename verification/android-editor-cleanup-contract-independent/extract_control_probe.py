#!/usr/bin/env python3
"""Run two exact canonical coordinator methods with authored host-only leaves.

This witnesses the current direct leave/dispose control route. The native editor
on-stack condition is authored; no Android runtime or complete coordinator runs.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCE = ROOT / "native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java"
JDK = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin")


def method(text, signature):
    start = text.index(signature)
    left = text.index("{", start)
    depth = 1
    end = left + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def main():
    raw = SOURCE.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    source = raw.decode()
    snippets = [method(source, signature) for signature in (
        "private void leave()", "private void disposeOnce()", "private void remember(Throwable failure)")]
    java = """public final class ControlProbe {
  enum Outcome { ATTEMPTED, RETURNED, FAILED_UNCERTAIN }
  static final class Fence { boolean rendererReportActive; }
  static final class Ledger {
    Throwable primary, rendererFailure, engineFailure; Error firstFatal;
    Outcome renderer, engine;
  }
  static final class Renderer {
    int calls; boolean editorNativeOnStack, observedOnStack;
    void disposeV2() { calls++; observedOnStack = editorNativeOnStack; }
  }
  static final class NativeBridge { static int destroyed; static void destroy(long v) { destroyed++; } }
  final Fence fence = new Fence(); final Ledger ledger = new Ledger(); final Renderer renderer = new Renderer();
  boolean active, retired, disposed, cancellation;
  Object operation; long session = 1; byte[] committedPacket;
""" + "\n".join(snippets) + """
  public static void main(String[] args) {
    ControlProbe unprotected = new ControlProbe();
    unprotected.retired = true; unprotected.renderer.editorNativeOnStack = true;
    unprotected.leave();
    if (unprotected.renderer.calls != 1 || !unprotected.renderer.observedOnStack || NativeBridge.destroyed != 1)
      throw new AssertionError("expected direct disposal while authored editor call remains on stack");
    ControlProbe cancellationProtected = new ControlProbe();
    cancellationProtected.retired = true; cancellationProtected.cancellation = true;
    cancellationProtected.leave();
    if (cancellationProtected.renderer.calls != 0) throw new AssertionError("existing cancellation guard");
    ControlProbe reportProtected = new ControlProbe();
    reportProtected.retired = true; reportProtected.fence.rendererReportActive = true;
    reportProtected.leave();
    if (reportProtected.renderer.calls != 0) throw new AssertionError("existing terminal-report guard");
    System.out.println("3 source-control groups passed: direct editor-stack hazard witnessed, existing cancellation/report guards preserved");
  }
}
"""
    generated = BASE / "probe-source"
    generated.mkdir(exist_ok=True)
    path = generated / "ControlProbe.java"
    path.write_text(java)
    records = []
    with tempfile.TemporaryDirectory(prefix="mixer-independent-source-controls-") as classes:
        commands = [
            [str(JDK / "javac"), "-version"],
            [str(JDK / "javac"), "-d", classes, str(path)],
            [str(JDK / "java"), "-cp", classes, "ControlProbe"],
        ]
        for number, command in enumerate(commands):
            result = subprocess.run(command, text=True, capture_output=True)
            (BASE / f"control-{number}.stdout.txt").write_text(result.stdout)
            (BASE / f"control-{number}.stderr.txt").write_text(result.stderr)
            records.append({"argv": command, "exit": result.returncode,
                            "stdout": f"control-{number}.stdout.txt", "stderr": f"control-{number}.stderr.txt"})
            if result.returncode:
                raise RuntimeError(f"command {number} failed")
    report = {"schema": 1, "python": sys.version, "canonical_source": str(SOURCE.relative_to(ROOT)),
              "canonical_sha256": actual, "extracted": [
                  {"signature": x.split("{")[0].strip(), "sha256": hashlib.sha256(x.encode()).hexdigest()}
                  for x in snippets], "commands": records,
              "scope": "Exact source leave/dispose/remember controls with authored host leaves only; observed existing hazard, not proposed implementation proof or Android runtime"}
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != actual:
        raise RuntimeError("canonical source moved during probe")
    (BASE / "source-control-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(records[-1])


if __name__ == "__main__":
    main()
