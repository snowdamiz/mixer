import {run,commands} from "./toy-helper.mjs";
import {writeFile} from "node:fs/promises";
import {join} from "node:path";
const originalKill=process.kill.bind(process),originalTimeout=globalThis.setTimeout;
process.kill=(target,signal)=>{if(target<0 && signal!==0){const error=new Error("injected EPERM denied signal");error.code="EPERM";throw error;}return originalKill(target,signal);};
globalThis.setTimeout=(callback,ms,...args)=>originalTimeout(callback,ms===300000?100:ms===305000?150:ms===310000?200:ms===5000?150:ms,...args);
let failure=null;
try{await run("denied-termination-ceiling",["-e",'setInterval(()=>{},1000);']);}catch(error){failure=error.message;}finally{process.kill=originalKill;globalThis.setTimeout=originalTimeout;}
await writeFile(join(import.meta.dirname,"returned.json"),JSON.stringify({failure,record:commands.at(-1)},null,2)+"\n");
console.log("ceiling-returned");
