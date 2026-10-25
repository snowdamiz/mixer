import {Env} from "./operation.js";
import {ingress,operationKey} from "./principal.js";
import {errorResponse} from "./wire.js";
export {MixerWorkerOperation} from "./operation.js";
export default {
  async fetch(request:Request,env:Env):Promise<Response>{
    let timer:ReturnType<typeof setTimeout>|undefined;
    const controller=new AbortController();
    const timeout=new Promise<Response>(resolve=>{timer=setTimeout(()=>{controller.abort();resolve(errorResponse(503));},4000);});
    const work=async():Promise<Response>=>{
    try{
      const checked=await ingress(request,env);if(checked instanceof Response)return checked;
      if(controller.signal.aborted)return errorResponse(503);
      const key=await operationKey(checked.r),id=env.OPERATIONS.idFromName(key);
      if(controller.signal.aborted)return errorResponse(503);
      return await env.OPERATIONS.get(id).fetch(new Request(request.url,{method:"POST",headers:request.headers,body:checked.bytes,signal:controller.signal}));
    }catch{return errorResponse(503);}
    };
    try{return await Promise.race([work(),timeout]);}finally{if(timer!==undefined)clearTimeout(timer);}
  }
};
