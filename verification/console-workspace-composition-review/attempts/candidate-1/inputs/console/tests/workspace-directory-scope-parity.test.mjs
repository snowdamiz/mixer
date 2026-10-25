import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { isWorkspaceIdentifier, parseWorkspaceOrganizations } from "../src/domain/workspace-directory.ts";

test("identifier Unicode/control/noncharacter acceptance matches the actual standalone Elixir Scope helper", () => {
  const vectors = ["", "*", "**", ".", "..", "a/b:c", "  ", "日本語", "e\u0301", "é".repeat(64),
    "é".repeat(65), "😀".repeat(32), "😀".repeat(33), "x".repeat(128), "x".repeat(129)].map(value => ({ value, bytes: Buffer.from(value) }));
  for (const code of [0, 7, 9, 10, 13, 27, 31, 32, 33, 47, 58, 126, 127, 128, 159, 160, 173,
    0x61c, 0x200b, 0x2028, 0x2029, 0x202e, 0xd7ff, 0xe000, 0xfdd0, 0xfdef,
    0xfffd, 0xfffe, 0xffff, 0x10000, 0x1fffe, 0x10fffd, 0x10fffe, 0x10ffff]) {
    const value = String.fromCodePoint(code);
    for (const text of [value, `a${value}b`]) vectors.push({ value: text, bytes: Buffer.from(text) });
  }
  // JS lone surrogates and their invalid UTF-8 byte sequences must both fail.
  vectors.push({ value: "\ud800", bytes: Buffer.from([0xed, 0xa0, 0x80]) },
    { value: "\udfff", bytes: Buffer.from([0xed, 0xbf, 0xbf]) });
  const binaries = vectors.map(({ bytes }) => `Base.decode64!("${bytes.toString("base64")}")`).join(",");
  const code = `[${binaries}] |> Enum.with_index() |> Enum.each(fn {value, index} -> IO.puts("#{index}=#{MixerHosted.Authorization.Scope.identifier?(value)}") end)`;
  const scope = fileURLToPath(new URL("../../hosted/lib/mixer_hosted/authorization/scope.ex", import.meta.url));
  // Only this ordinary, standalone helper is loaded. No hosted application or runtime starts.
  const output = execFileSync("elixir", ["-r", scope, "-e", code], { encoding: "utf8", timeout: 15000 });
  const answers = output.trim().split("\n").map(line => line.split("="));
  assert.equal(answers.length, vectors.length);
  for (const [index, answer] of answers) {
    const value = vectors[Number(index)].value;
    let accepted = true;
    try { parseWorkspaceOrganizations({ organizations: [{ id: value, display_name: null, organization_roles: [] }], next_cursor: null }); }
    catch { accepted = false; }
    assert.equal(accepted, answer === "true", `Scope mismatch for ${JSON.stringify(value)}`);
    assert.equal(isWorkspaceIdentifier(value), answer === "true", `Exported predicate mismatch for ${JSON.stringify(value)}`);
  }
});
