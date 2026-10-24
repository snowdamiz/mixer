import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { cp, mkdir, readFile, readdir, writeFile, symlink, readlink, unlink } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const packet = fileURLToPath(new URL("./", import.meta.url));
const workspace = resolve(packet, "../..");
const consoleRoot = join(workspace, "console");
const snapshot = join(packet, "production-source-snapshot");
const output = join(packet, "production-dist");
const sha = value => createHash("sha256").update(value).digest("hex");
function effectiveRootTokens(css) {
  const tokens = {};
  for (const match of css.matchAll(/^:root\s*\{([^}]+)\}/gm)) {
    for (const declaration of match[1].split(";")) {
      const colon = declaration.indexOf(":");
      const name = declaration.slice(0, colon).trim();
      if (name.startsWith("--")) tokens[name] = declaration.slice(colon + 1).trim();
    }
  }
  return tokens;
}
async function filesUnder(dir, prefix = "") {
  const result = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const relative = join(prefix, entry.name);
    if (entry.isDirectory()) result.push(...await filesUnder(join(dir, entry.name), relative));
    else if (entry.isFile()) result.push(relative);
    else throw new Error(`Unexpected non-file in source: ${join(dir, entry.name)}`);
  }
  return result;
}
const sourceFiles = ["index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts",
  ...(await filesUnder(join(consoleRoot, "src"), "src"))];
try { sourceFiles.push(...await filesUnder(join(consoleRoot, "public"), "public")); }
catch (error) { if (error.code !== "ENOENT") throw error; }
sourceFiles.sort();
const hashes = {};
await mkdir(snapshot, { recursive: true });
for (const file of sourceFiles) {
  await cp(join(consoleRoot, file), join(snapshot, file), { recursive: true });
  hashes[`console/${file}`] = sha(await readFile(join(snapshot, file)));
}
const websiteStyles = await readFile(join(workspace, "website/src/styles.css"), "utf8");
const websiteTokens = effectiveRootTokens(websiteStyles);
const consoleTokens = effectiveRootTokens(await readFile(join(snapshot, "src/brand.css"), "utf8"));
for (const [token, value] of Object.entries(websiteTokens)) assert.equal(consoleTokens[token], value, `Effective website token differs: ${token}`);
for (const name of ["flick-128.webp", "favicon-32.png"]) assert.equal(sha(await readFile(join(snapshot, "public/assets", name))), sha(await readFile(join(workspace, "website/public/assets", name))), `Website logo asset differs: ${name}`);
try { await symlink(join(consoleRoot, "node_modules"), join(snapshot, "node_modules"), "dir"); }
catch (error) { if (error.code !== "EEXIST") throw error; }
assert.equal(await readlink(join(snapshot, "node_modules")), join(consoleRoot, "node_modules"));
const { build } = await import(pathToFileURL(join(consoleRoot, "node_modules/vite/dist/node/index.js")));
try {
  const typecheck = spawnSync(process.execPath, [join(consoleRoot, "node_modules/typescript/bin/tsc"), "--noEmit", "--project", join(snapshot, "tsconfig.json")], { encoding: "utf8" });
  await writeFile(join(packet, "isolated-typecheck.stdout"), typecheck.stdout);
  await writeFile(join(packet, "isolated-typecheck.stderr"), typecheck.stderr);
  assert.equal(typecheck.status, 0, typecheck.stderr || typecheck.stdout);
  await build({ root: snapshot, configFile: join(snapshot, "vite.config.ts"),
    build: { outDir: output, emptyOutDir: true } });
} finally { await unlink(join(snapshot, "node_modules")); }
for (const file of sourceFiles) assert.equal(sha(await readFile(join(consoleRoot, file))), hashes[`console/${file}`], `Source changed during build: ${file}`);
const outputFiles = (await filesUnder(output)).sort();
const scriptFiles = outputFiles.filter(file => /\.js$/.test(file));
assert.ok(scriptFiles.length > 0);
const scripts = (await Promise.all(scriptFiles.map(file => readFile(join(output, file), "utf8")))).join("\n");
const markers = ["sample-current-7c81d9a", "sample-previous-391dbf0", "ios-26-build-42", "android-build-42", "Synthetic release data", "Local preview", "Example state"];
for (const marker of markers) assert.ok(!scripts.includes(marker), `Preview data leaked into production bundle: ${marker}`);
assert.ok(!outputFiles.some(file => file.includes("ReleaseChecksPreview")), "Preview chunk was emitted");
assert.ok(scripts.includes("Release data unavailable"));
assert.ok(scripts.includes("No release data source is connected"));
const manifest = {
  baseRevision: "c628863f7dc3dc3b694d2949be6176a311cce04c",
  baseRevisionSource: "root agent message; reviewer did not use Git",
  capturedAt: new Date().toISOString(),
  sourceFiles: hashes,
  treeDigest: sha(Object.entries(hashes).map(([file, hash]) => `${file}\0${hash}\n`).join("")),
  treeDigestMethod: "sha256 of sorted console-relative path + NUL + sha256 + LF entries",
  artifacts: Object.fromEntries(await Promise.all(outputFiles.map(async file => [file, sha(await readFile(join(output, file)))]))),
  productionAssertions: { syntheticMarkersAbsent: markers, previewChunkAbsent: true,
    unavailableCopyPresent: true, previewRouteLiteralPresent: scripts.includes("/preview/release-checks"),
    routeRuntimeAvailability: "not executed by independent source/host review; root browser receipt required" },
  brandAssertions: { websiteStyleSha256: sha(websiteStyles), effectiveRootTokens: websiteTokens,
    consoleTokensMatchEffectiveWebsiteTokens: true, logoAndFaviconBytesMatchWebsite: true },
};
await writeFile(join(packet, "source-and-artifact-manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(JSON.stringify({ treeDigest: manifest.treeDigest, sourceFileCount: sourceFiles.length,
  artifactFileCount: outputFiles.length, productionAssertions: manifest.productionAssertions }, null, 2));
