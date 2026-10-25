import {spawnSync} from 'node:child_process';
import {copyFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'../../..');
const result=spawnSync(process.execPath,[resolve(root,'hosted-worker-controller/node_modules/typescript/bin/tsc'),'-p',resolve(import.meta.dirname,'tsconfig.json')],{stdio:'inherit'});
if(result.status!==0)process.exit(result.status??1);
await mkdir(resolve(import.meta.dirname,'dist/src'),{recursive:true});
await copyFile(resolve(import.meta.dirname,'src/registry-schema.sql'),resolve(import.meta.dirname,'dist/src/registry-schema.sql'));
