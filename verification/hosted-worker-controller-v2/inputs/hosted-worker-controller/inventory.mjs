// Lockfile-only inventory; no registry request, package script or tool execution.
import {readFile,writeFile} from "node:fs/promises";
const lock=JSON.parse(await readFile(new URL("package-lock.json",import.meta.url),"utf8"));
const direct=new Set(["miniflare","@cloudflare/workers-types","typescript"]);
const packages=Object.entries(lock.packages).filter(([path])=>path).map(([path,p])=>{
  if(!p.version||!p.license||!p.integrity)throw new Error("incomplete_locked_inventory");
  const name=path.slice(path.lastIndexOf("node_modules/")+13);
  let purpose="Transitive local Miniflare test support; not a production dependency";
  if(name==="typescript")purpose="Pinned TypeScript compiler for the owned Worker and excluded test bundle";
  else if(name==="@cloudflare/workers-types")purpose="Pinned compile-time Workers and SQLite Durable Object API declarations";
  else if(name==="miniflare")purpose="Local workerd process orchestration and persisted SQLite Durable Object tests";
  else if(name==="workerd"||name.startsWith("@cloudflare/workerd-"))purpose="Pinned native local Workers runtime; optional binaries cover supported installation targets";
  else if(name==="sharp"||name.startsWith("@img/")||name==="detect-libc"||name==="semver")purpose="Miniflare transitive image/tooling support; no image API used by this controller slice";
  return {name,version:p.version,license:p.license,scope:"development-only",direct:direct.has(name),purpose,
    lockPath:path,resolved:p.resolved,integrity:p.integrity,optional:!!p.optional,os:p.os??null,cpu:p.cpu??null,
    installScriptPresent:!!p.hasInstallScript,installScriptsExecuted:false};
});
await writeFile(new URL("THIRD_PARTY.yml",import.meta.url),JSON.stringify({schema:1,project:"Mixer hosted worker controller",format:"JSON-compatible YAML",runtimeProductionDependencies:[],
  installPolicy:"npm install/ci --ignore-scripts; no dependency script executed",packages},null,2)+"\n");
console.log(JSON.stringify({lockedPackages:packages.length,directDevelopmentDependencies:3,missingLicenses:0,dependencyScriptsExecuted:0}));
