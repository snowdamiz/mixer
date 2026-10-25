import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
const r=spawnSync('python3',[resolve(import.meta.dirname,'../run.py')],{stdio:'inherit'});
process.exitCode=r.status??1;
