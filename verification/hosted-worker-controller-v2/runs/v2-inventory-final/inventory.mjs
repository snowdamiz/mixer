// Read-only exact lock/inventory check. No registry, installation or scripts.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
const project=process.cwd(),here=process.env.MIXER_V2_RUN_DIR;
const lock=JSON.parse(await readFile(join(project,'package-lock.json'),'utf8'));
const inventory=JSON.parse(await readFile(join(project,'THIRD_PARTY.yml'),'utf8'));
const entries=new Map(inventory.packages.map(e=>[e.lockPath,e]));
assert.equal(entries.size,58);assert.equal(Object.keys(lock.packages).length,59);
for(const [path,e]of Object.entries(lock.packages)){
 if(!path)continue;const d=entries.get(path);assert(d);
 for(const key of ['version','license','resolved','integrity'])assert.equal(d[key],e[key],path+':'+key);
 assert(d.purpose);assert.equal(d.scope,'development-only');assert.equal(d.installScriptsExecuted,false);
}
assert.deepEqual(inventory.runtimeProductionDependencies,[]);
const versions={node:process.version,npm:execFileSync(process.execPath,[join(process.execPath,'../npm'),'--version'],{encoding:'utf8'}).trim()};
for(const name of ['typescript','miniflare','workerd','@cloudflare/workers-types'])versions[name]=JSON.parse(await readFile(join(project,'node_modules',name,'package.json'),'utf8')).version;
assert.equal(versions.node,'v22.23.3');assert.equal(versions.npm,'10.9.9');assert.equal(versions.typescript,'5.9.3');assert.equal(versions.miniflare,'4.20260730.0');assert.equal(versions.workerd,'1.20260730.1');assert.equal(versions['@cloudflare/workers-types'],'5.20260730.1');
const workerd=join(project,'node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd');
const report={status:'passed',locked_entries:58,versions,compiler_version:execFileSync(process.execPath,[join(project,'node_modules/typescript/bin/tsc'),'--version'],{encoding:'utf8'}).trim(),workerd_version:execFileSync(workerd,['--version'],{encoding:'utf8'}).trim(),os:execFileSync('/usr/bin/sw_vers',[],{encoding:'utf8'}),dependency_installs:0,install_scripts_executed:0,production_dependencies:0,authorizationGate:false};
await writeFile(join(here,'inventory-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
