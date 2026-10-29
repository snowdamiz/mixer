import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
// Pure filesystem work only. The caller owns host command custody and cleanup.
export async function materialize(output, repo=path.resolve(here,'../..')) {
  assert.equal(typeof output,'string');assert(path.isAbsolute(output));
  const dest=path.resolve(output), base=path.resolve(repo);
  assert(dest!==base&&!dest.startsWith(base+path.sep),'scratch must be outside the repository');
  const parent=await fs.lstat(path.dirname(dest));assert(parent.isDirectory()&&!parent.isSymbolicLink(),'existing real parent required');
  const existing=await fs.lstat(dest).catch(e=>{if(e.code!=='ENOENT')throw e;return null;});
  assert.equal(existing,null,'fresh scratch only; never overwrite');
  const m=JSON.parse(await fs.readFile(path.join(here,'manifest.json'),'utf8'));
  const contents=[];
  for(const [name,row] of Object.entries(m.baselineFiles)) {
    assert(!path.isAbsolute(name)&&!name.split('/').includes('..'));
    const src=path.join(base,'vm',name), stat=await fs.lstat(src);assert(stat.isFile()&&!stat.isSymbolicLink());
    const baseline=await fs.readFile(src);assert.equal(baseline.length,row.bytes,name);assert.equal(sha(baseline),row.sha256,name);
    const data=m.overlayPaths.includes(name)?await fs.readFile(path.join(here,'candidate/vm',name)):baseline;
    const expected=m.candidateFiles[name];assert.equal(data.length,expected.bytes,name);assert.equal(sha(data),expected.sha256,name);
    contents.push([name,data]);
  }
  for(const [name,row] of Object.entries(m.protectedFiles))assert.equal(sha(await fs.readFile(path.join(base,name))),row.sha256,name);
  await fs.mkdir(dest); // exclusive ownership begins only after complete input validation
  for(const [name,data] of contents){const target=path.join(dest,name);await fs.mkdir(path.dirname(target),{recursive:true});await fs.writeFile(target,data,{flag:'wx'});}
  return {path:dest,files:contents.length,sourceTreeSHA256:m.candidateTreeSHA256,compilations:0,runtimeRuns:0};
}
