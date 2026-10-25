import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
const require=createRequire(new URL('../../hosted-worker-controller/package.json',import.meta.url));
const dependencies={};for(const name of ['typescript','miniflare','workerd','@cloudflare/workers-types'])dependencies[name]=JSON.parse(await readFile(resolve(import.meta.dirname,'../../hosted-worker-controller/node_modules',name,'package.json'),'utf8')).version;
const commands=[];for(const [cmd,args] of [[require('workerd').default,['--version']],['/usr/bin/uname',['-a']],['/usr/bin/sw_vers',[]]]){const r=spawnSync(cmd,args,{encoding:'utf8',timeout:5000});commands.push({command:[cmd,...args],exitCode:r.status,stdout:r.stdout,stderr:r.stderr,stdoutEOF:true,stderrEOF:true});if(r.status!==0)throw new Error('version_command_failed');}
const result={node:process.version,executable:process.execPath,platform:process.platform,architecture:process.arch,dependencies,commands};await writeFile(resolve(import.meta.dirname,'tool-versions.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
