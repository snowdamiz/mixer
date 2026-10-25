import assert from "node:assert/strict";
import test from "node:test";
import { summarizeBuildOverview } from "../src/domain/build-overview.ts";
import { inputForText, textCases } from "./build-overview-text-cases.mjs";

test("text follows Lifecycle UTF-8 byte limits and Elixir printable Unicode without normalization", () => {
  for (const { field, label, value, accepted } of textCases) {
    const input = inputForText(field, value);
    if (!accepted) assert.throws(() => summarizeBuildOverview(input), TypeError, `${field}: ${label}`);
    else {
      const result = summarizeBuildOverview(input);
      const actual = field === "sourceReference" ? result.builds[0].target.source.reference :
        field === "buildId" ? result.builds[0].target.buildId : result.scope[field];
      assert.equal(actual, value, `${field}: ${label}`);
    }
  }
});
