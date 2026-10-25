import {spawnSync} from "node:child_process";
import {copyFile,mkdir} from "node:fs/promises";
const result=spawnSync(process.execPath,["node_modules/typescript/bin/tsc","-p","tsconfig.json"],{stdio:"inherit"});
if(result.status!==0)process.exit(result.status??1);
await mkdir("dist/src",{recursive:true});
for (const name of ["schema.sql", "registry-schema.sql"]) {
  await copyFile(`src/${name}`, `dist/src/${name}`);
}
