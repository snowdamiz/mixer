// Mixer-owned v1 codec. No authorization or provider execution is inferred here.
export const MAX = 9223372036854775807n;
export const encoder = new TextEncoder();
export class InvalidInput extends Error { constructor() { super("invalid_input"); this.name="InvalidInput"; } }
export function invalid():never { throw new InvalidInput(); }
export function exact(v: unknown, keys: readonly string[]): asserts v is Record<string, unknown> {
  if (!v || typeof v!=="object" || Array.isArray(v) || Object.keys(v).length!==keys.length || !keys.every(k=>Object.hasOwn(v,k))) invalid();
}
export function decimal(v: unknown, min=1n, max=MAX): string {
  if(typeof v!=="string" || v.length>19 || !/^(0|[1-9][0-9]*)$/.test(v)) invalid();
  const n=BigInt(v); if(n<min || n>max) invalid(); return v;
}
export function text(v: unknown, max=128): string {
  if(typeof v!=="string" || !v.length || encoder.encode(v).length>max) invalid();
  // Elixir printable UTF-8 repertoire, without normalization or surrogate repair.
  for(const ch of v) {
    const c=ch.codePointAt(0)!;
    if(!((c>=32&&c<=127)||(c>=160&&c<=0xd7ff)||(c>=0xe000&&c<=0xfffd)||
      (c>=0x10000&&c<=0x10ffff)||(c>=7&&c<=13)||c===27)) invalid();
  }
  return v;
}
export function hex(v: unknown, length=64): string {
  if(typeof v!=="string"||v.length!==length||!/^[0-9a-f]+$/.test(v)) invalid();return v;
}
const scopeKeys=["organization_id","project_id","application_id","build_id","platform"] as const;
export interface Scope { organization_id:string;project_id:string;application_id:string;build_id:string;platform:"ios"|"android" }
export interface Ref extends Scope { attempt:number;fence:string }
export interface Spec extends Scope { source:{kind:"revision"|"upload";sha256:string;reference:string}; toolchain_lock_sha256:string;build_definition_sha256:string }
export interface Guard {record_id:string;revision:string;owner_id:string;epoch:string;expires_at_us:string}
export interface WireRequest { version:1;environment_id:string;pool_id:string;controller_id:string;request_id:string;command:"query"|"ensure_started"|"stop";operation_id:string;immutable_sha256:string;ref:Ref;spec:Spec;deadline_ms:string;guard:Guard }
export type Observation = {status:"absent"|"running"}|{status:"error";code:"stale"|"unavailable"|"uncertain"}|{status:"stopped";diagnostic_sha256:string}|{status:"completed";result:BuildResult};
export type BuildResult = {outcome:"succeeded";artifacts:{kind:string;sha256:string;size_bytes:string}[]}|{outcome:"failed";class:string;code:string;diagnostic_sha256:string};

// This parser counts depth/tokens/raw string bytes before allocating decoded
// strings/objects. JSON.parse is used only for a bounded single string token.
export function parseJSON(raw: Uint8Array, limit=16384): unknown {
  if(!raw.byteLength||raw.byteLength>limit) invalid();
  let source:string;try{source=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(raw);}catch{invalid();}
  let i=0,tokens=0;
  const ws=()=>{while(i<source.length&&" \n\r\t".includes(source[i]!))i++;};
  const token=()=>{if(++tokens>512)invalid();};
  const str=():string=>{
    const start=i++;let escaped=false;
    while(i<source.length){const c=source[i++]!;
      if(!escaped&&c==='"'){
        const slice=source.slice(start,i);if(encoder.encode(slice.slice(1,-1)).length>8192)invalid();
        let value:unknown;try{value=JSON.parse(slice);}catch{invalid();}
        return value as string;
      }
      if(!escaped&&c==="\\")escaped=true;else escaped=false;
    }return invalid();
  };
  const value=(depth:number):unknown=>{
    ws();token();if(depth>8)invalid();const c=source[i];
    if((c==="{"||c==="[")&&depth>=8)invalid();
    if(c==='"')return str();
    if(c==="{"){
      i++;const result:Record<string,unknown>=Object.create(null);ws();if(source[i]==="}"){i++;return result;}
      while(true){ws();token();if(source[i]!=='"')invalid();const key=str();if(Object.hasOwn(result,key))invalid();ws();if(source[i++]!==":")invalid();result[key]=value(depth+1);ws();const sep=source[i++];if(sep==="}")return result;if(sep!==",")invalid();}
    }
    if(c==="["){
      i++;const result:unknown[]=[];ws();if(source[i]==="]"){i++;return result;}
      while(true){result.push(value(depth+1));ws();const sep=source[i++];if(sep==="]")return result;if(sep!==",")invalid();}
    }
    const start=i;while(i<source.length&&!" \t\n\r,]}".includes(source[i]!))i++;
    const literal=source.slice(start,i);
    if(literal==="true")return true;if(literal==="false")return false;if(literal==="null")return null;
    // Protocol numbers are only small integer version/attempt tokens.
    if(!/^(0|[1-9][0-9]*)$/.test(literal))invalid();
    const n=Number(literal);if(!Number.isSafeInteger(n))invalid();return n;
  };
  const result=value(0);ws();if(i!==source.length)invalid();return result;
}
function scope(v:Record<string,unknown>):void {
  for(const key of scopeKeys)if(key!=="platform")text(v[key]);
  if(v.platform!=="ios"&&v.platform!=="android")invalid();
}
export async function sha(s:string|Uint8Array):Promise<string>{
  const bytes=typeof s==="string"?encoder.encode(s):s;
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  return Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,"0")).join("");
}
// Exact default Jason string bytes are part of the frozen hash contract.
// JSON.stringify differs for printable \v/\e: Jason's Unicode escapes use
// uppercase hex. Walk characters so literal text such as "\\u000b" is untouched.
function hashString(value:string):string {
  let out='"';const short:Record<number,string>={8:"\\b",9:"\\t",10:"\\n",12:"\\f",13:"\\r"};
  for(const ch of value){const cp=ch.codePointAt(0)!;
    if(ch==='"')out+='\\"';else if(ch==='\\')out+='\\\\';
    else if(cp<32)out+=short[cp]??"\\u"+cp.toString(16).toUpperCase().padStart(4,"0");else out+=ch;
  }return out+'"';
}
function hashArray(value:unknown[]):string {
  return "["+value.map(v=>Array.isArray(v)?hashArray(v):typeof v==="string"?hashString(v):
    typeof v==="number"&&Number.isSafeInteger(v)?String(v):invalid()).join(",")+"]";
}
export function immutableBytes(r:WireRequest):string {
  const f=r.ref,s=r.spec;
  return hashArray(["mixer-worker-binding-v1",r.operation_id,r.guard.record_id,
    [f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt,f.fence],
    [s.organization_id,s.project_id,s.application_id,s.build_id,s.platform,s.source.kind,s.source.sha256,s.source.reference,s.toolchain_lock_sha256,s.build_definition_sha256],r.deadline_ms]);
}
export function operationBytes(r:WireRequest):string {
  const f=r.ref;
  const prefix=hashArray(["mixer-build-operation-v1",r.guard.record_id,f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt]);
  return prefix.slice(0,-1)+","+decimal(f.fence)+"]";
}
export async function decode(raw:Uint8Array):Promise<WireRequest>{
  const v=parseJSON(raw);exact(v,["version","environment_id","pool_id","controller_id","request_id","command","operation_id","immutable_sha256","ref","spec","deadline_ms","guard"]);
  if(v.version!==1||!["query","ensure_started","stop"].includes(v.command as string))invalid();
  for(const k of ["environment_id","pool_id","controller_id"]) {const t=text(v[k]);if(!/^[\x20-\x7e]+$/.test(t))invalid();}
  hex(v.request_id,32);hex(v.operation_id);hex(v.immutable_sha256);decimal(v.deadline_ms);
  exact(v.ref,[...scopeKeys,"attempt","fence"]);scope(v.ref);
  if(!Number.isInteger(v.ref.attempt)||(v.ref.attempt as number)<1||(v.ref.attempt as number)>5)invalid();decimal(v.ref.fence);
  exact(v.spec,[...scopeKeys,"source","toolchain_lock_sha256","build_definition_sha256"]);scope(v.spec);
  const f=v.ref,s=v.spec;if(!scopeKeys.every(k=>f[k]===s[k]))invalid();
  hex(v.spec.toolchain_lock_sha256);hex(v.spec.build_definition_sha256);
  exact(v.spec.source,["kind","sha256","reference"]);if(v.spec.source.kind!=="revision"&&v.spec.source.kind!=="upload")invalid();hex(v.spec.source.sha256);text(v.spec.source.reference,1024);
  exact(v.guard,["record_id","revision","owner_id","epoch","expires_at_us"]);
  if(typeof v.guard.record_id!=="string"||! /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v.guard.record_id))invalid();
  decimal(v.guard.revision,0n,32n);decimal(v.guard.epoch);decimal(v.guard.expires_at_us);text(v.guard.owner_id);
  const r=v as unknown as WireRequest;
  if(await sha(operationBytes(r))!==r.operation_id||await sha(immutableBytes(r))!==r.immutable_sha256)invalid();
  return r;
}
export function reply(r:WireRequest,observation:Observation):Response {
  const {spec:discard,deadline_ms:discard2,...echo}=r;
  const bytes=encoder.encode(JSON.stringify({...echo,observation}));
  if(bytes.length>32768)throw new Error("response_limit");
  return new Response(bytes,{status:200,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
}
export const errorResponse=(status:number):Response=>new Response('{"error":"rejected"}',{status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
const kinds=["unsigned_native_binary","guest_artifact","resource_inventory","debug_symbols","compatibility_report","sbom","provenance"];
const failures:Record<string,string[]>={infrastructure:["worker_unavailable","worker_lost","dependency_transport","artifact_transport","worker_timeout"],compiler:["compiler_error"],test:["test_failure"],policy:["policy_rejection","invalid_input"],unknown:["unknown_failure"]};
export function result(v:unknown):BuildResult {
  if(!v||typeof v!=="object")invalid();const r=v as Record<string,unknown>;
  if(r.outcome==="succeeded") {
    exact(r,["outcome","artifacts"]);if(!Array.isArray(r.artifacts)||r.artifacts.length!==7)invalid();
    const seen=new Set(),sizes=new Map<string,string>();
    for(const a of r.artifacts){exact(a,["kind","sha256","size_bytes"]);if(!kinds.includes(a.kind as string)||seen.has(a.kind))invalid();seen.add(a.kind);const h=hex(a.sha256),n=decimal(a.size_bytes);if(sizes.has(h)&&sizes.get(h)!==n)invalid();sizes.set(h,n);}
  } else {
    exact(r,["outcome","class","code","diagnostic_sha256"]);if(r.outcome!=="failed"||typeof r.class!=="string"||typeof r.code!=="string"||!Object.hasOwn(failures,r.class)||!failures[r.class]!.includes(r.code))invalid();hex(r.diagnostic_sha256);
  }return r as unknown as BuildResult;
}
