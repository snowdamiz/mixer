import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { summarizeBuildOverview } from "../../console/src/domain/build-overview.ts";
import { inputForText, textCases } from "../../console/tests/build-overview-text-cases.mjs";

const root = fileURLToPath(new URL("../../", import.meta.url));
const vectors = textCases.map((item, index) => `${index}\t${item.field}\t${item.invalidUtf8Hex ?? Buffer.from(item.value, "utf8").toString("hex")}`).join("\n") + "\n";
const args = ["-r", "hosted/lib/mixer_hosted/builds/lifecycle.ex", "verification/console-build-overview/text-boundaries.exs"];
const result = spawnSync("elixir", args, { cwd: root, input: vectors, encoding: "utf8",
  env: { ...process.env, ERL_FLAGS: "+S 2:2" } });
if (result.error) throw result.error;
assert.equal(result.status, 0, result.stderr);
const lines = result.stdout.trimEnd().split("\n");
assert.equal(lines.length, textCases.length);
for (const [index, item] of textCases.entries()) {
  const [reportedIndex, accepted] = lines[index].split("\t");
  assert.equal(Number(reportedIndex), index);
  assert.equal(accepted, String(item.accepted), `${item.field}: ${item.label}: Elixir`);
  let displayAccepted;
  try { summarizeBuildOverview(inputForText(item.field, item.value)); displayAccepted = true; }
  catch (error) { if (!(error instanceof TypeError)) throw error; displayAccepted = false; }
  assert.equal(displayAccepted, item.accepted, `${item.field}: ${item.label}: TypeScript`);
}
console.log(JSON.stringify({ command: ["elixir", ...args], vectors: textCases.length,
  matches: textCases.length, scope: "actual Lifecycle.new versus internal TypeScript display boundary",
  includes: ["128/1024 UTF-8 byte bounds", "multibyte/astral text", "whitespace preservation", "printable Unicode controls", "invalid surrogate UTF-8"] }, null, 2));
