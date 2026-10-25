const cases = [];
const fields = ["organizationId", "projectId", "applicationId", "buildId"];
const add = (field, label, value, accepted, invalidUtf8Hex) => cases.push({ field, label, value, accepted,
  ...(invalidUtf8Hex ? { invalidUtf8Hex } : {}) });
for (const field of fields) {
  for (const [label, character, boundary] of [["ASCII", "x", 128], ["two-byte", "é", 64], ["astral", "😀", 32]]) {
    add(field, `${label} at byte limit`, character.repeat(boundary), true);
    add(field, `${label} above byte limit`, character.repeat(boundary + 1), false);
  }
}
for (const [label, character, boundary] of [["ASCII", "x", 1024], ["two-byte", "é", 512], ["astral", "😀", 256]]) {
  add("sourceReference", `${label} at byte limit`, character.repeat(boundary), true);
  add("sourceReference", `${label} above byte limit`, character.repeat(boundary + 1), false);
}
for (const field of [...fields, "sourceReference"]) {
  add(field, "empty text", "", false);
  add(field, "whitespace preserved", " \t\nidentity \r ", true);
  add(field, "whitespace only", " \t ", true);
  add(field, "lone high surrogate", "\ud800", false, "eda080");
  add(field, "lone low surrogate", "\udc00", false, "edb080");
}
const allowed = [0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1b, 0x20, 0x7e, 0x7f,
  0xa0, 0x200b, 0x2028, 0x202e, 0x2060, 0xd7ff, 0xe000, 0xfdd0, 0xfffd, 0x1f600, 0x10ffff];
const refused = [0x00, 0x06, 0x0e, 0x1f, 0x80, 0x85, 0x9f, 0xfffe, 0xffff];
for (const field of ["buildId", "sourceReference"]) {
  for (const [points, accepted] of [[allowed, true], [refused, false]]) for (const point of points) {
    add(field, `U+${point.toString(16).toUpperCase()}`, String.fromCodePoint(point), accepted);
  }
}
export const textCases = cases;

export function inputForText(field, value) {
  const scope = { organizationId: "organization", projectId: "project", applicationId: "application" };
  const target = { platform: "ios", buildId: "build", sourceSha256: "a".repeat(64),
    toolchainLockSha256: "b".repeat(64), buildDefinitionSha256: "c".repeat(64),
    source: { kind: "revision", reference: "main" } };
  if (field === "sourceReference") target.source.reference = value;
  else if (field === "buildId") target.buildId = value;
  else scope[field] = value;
  return { scope, expected: [target], reports: [] };
}
