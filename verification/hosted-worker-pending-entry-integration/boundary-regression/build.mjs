import {spawnSync} from 'node:child_process';
import {copyFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'../../..');
const r=spawnSync(process.execPath,[resolve(root,'hosted-worker-controller/node_modules/typescript/bin/tsc'),'-p',resolve(import.meta.dirname,'tsconfig.json')],{stdio:'inherit'});
if(r.status!==0)process.exit(r.status??1);
await mkdir(resolve(import.meta.dirname,'dist/src'),{recursive:true});
for(const f of ['schema.sql','registry-schema.sql'])await copyFile(resolve(import.meta.dirname,'src',f),resolve(import.meta.dirname,'dist/src',f));
