import {spawnSync} from "node:child_process";
import {copyFile,mkdir} from "node:fs/promises";
const result=spawnSync(process.execPath,["node_modules/typescript/bin/tsc","-p","tsconfig.json"],{stdio:"inherit"});
if(result.status!==0)process.exit(result.status??1);
await mkdir("dist/src",{recursive:true});
await copyFile("src/schema.sql","dist/src/schema.sql");
