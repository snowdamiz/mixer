// Source parsing only: no transform, compilation, typecheck, test or application start.
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, extname, relative, resolve } from "node:path";

const repository = resolve(process.argv[2]);
const manifest = JSON.parse(readFileSync(process.argv[3], "utf8"));
const require = createRequire(resolve(repository, "console/package.json"));
const parser = require("@babel/parser");
const parserPackage = require("@babel/parser/package.json");
const packageManifest = JSON.parse(readFileSync(resolve(repository, "console/package.json"), "utf8"));
const declaredPackages = new Set([...Object.keys(packageManifest.dependencies), ...Object.keys(packageManifest.devDependencies)]);
const findings = [];
const imports = [];
const sourceFiles = manifest.files.filter(file => /\.(?:mjs|ts|tsx)$/.test(file.path));
for (const file of sourceFiles) {
  const filename = resolve(repository, file.path);
  const source = readFileSync(filename, "utf8");
  const plugins = extname(filename) === ".mjs" ? [] : ["typescript", "jsx"];
  const tree = parser.parse(source, { sourceType: "module", plugins });
  const capture = (kind, node) => findings.push({ file: file.path, line: node.loc.start.line,
    kind, source: source.slice(node.start, node.end) });
  const recordImport = (value, node) => {
    const entry = { file: file.path, line: node.loc.start.line, specifier: value };
    if (value.startsWith(".")) {
      const base = resolve(dirname(filename), value);
      const candidates = [base, base.replace(/\.js$/, ".ts"), base.replace(/\.js$/, ".tsx")];
      const target = candidates.find(candidate => existsSync(candidate));
      assert.ok(target, `Unresolved relative source import: ${file.path} ${value}`);
      entry.resolved = relative(repository, target);
      assert.ok(entry.resolved.startsWith("console/"), `Import escapes console: ${entry.resolved}`);
      assert.ok(manifest.files.some(item => item.path === entry.resolved), `Import is outside sparse inputs: ${entry.resolved}`);
    } else if (!value.startsWith("node:")) {
      const parts = value.split("/");
      const packageName = value.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
      assert.ok(declaredPackages.has(packageName), `Undeclared package import: ${file.path} ${value}`);
    }
    imports.push(entry);
  };
  const visit = node => {
    if (!node || typeof node !== "object") return;
    if (["ImportDeclaration", "ExportNamedDeclaration", "ExportAllDeclaration"].includes(node.type) && node.source)
      recordImport(node.source.value, node);
    if (node.type === "CallExpression") {
      if (node.callee.type === "Import") {
        capture("dynamic-import", node);
        if (node.arguments[0]?.type === "StringLiteral") recordImport(node.arguments[0].value, node);
      }
      const name = node.callee.type === "Identifier" ? node.callee.name : node.callee.property?.name;
      if (["readFile", "readFileSync", "writeFileSync", "mkdtemp", "mkdtempSync", "mkdir", "mkdirSync", "rm", "rmSync", "existsSync", "execFileSync", "spawn", "build"].includes(name))
        capture(name, node);
    }
    if (node.type === "NewExpression" && node.callee.name === "URL") capture("new-URL", node);
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) {
        for (const child of value) if (child?.type) visit(child);
      } else if (value?.type) visit(value);
    }
  };
  visit(tree);
}
// This output supports manual source review. It is not a runtime test result.
process.stdout.write(JSON.stringify({ parser: `@babel/parser ${parserPackage.version}`,
  scope: "AST source imports and file/process/build call inventory; no compiler or test invoked",
  parsedFiles: sourceFiles.length, imports, findings }, null, 2) + "\n");
