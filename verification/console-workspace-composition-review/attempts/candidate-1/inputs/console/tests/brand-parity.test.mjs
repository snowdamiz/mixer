import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("console identity matches the existing Mixer website tokens and logo bytes", async () => {
  const root = new URL("../../", import.meta.url);
  const website = await readFile(new URL("website/src/styles.css", root), "utf8");
  const consoleBrand = await readFile(new URL("console/src/brand.css", root), "utf8");
  // The website refines its palette in a later block; first declarations alone
  // are not the effective identity. Retain every root declaration in order.
  const tokens = css => [...css.matchAll(/:root\{([^}]*)\}/g)].map(match => match[1]);
  assert.equal(tokens(website).length, 2);
  assert.deepEqual(tokens(consoleBrand), tokens(website));
  for (const name of ["flick-128.webp", "favicon-32.png"]) {
    assert.deepEqual(await readFile(new URL(`console/public/assets/${name}`, root)),
      await readFile(new URL(`website/public/assets/${name}`, root)));
  }
});
