import {BuildResult,WireRequest} from "./wire.js";
export interface ResourceIdentity {provider:"unavailable"|"cloudflare-linux"|"external-macos";key:string;immutableSha256:string}
export interface Effect {id:string;kind:"launch"|"inspect"|"stop";identity:ResourceIdentity;request:WireRequest}
export interface ProviderObservation {identity:ResourceIdentity;state:"absent"|"inert"|"running"|"unknown";instanceId:string|null;bootId:string|null;definitive:boolean;descendantsGone:boolean;launchesSettled:boolean;diagnosticSha256:string}
export interface Provider {readonly available:boolean;kind(platform:"ios"|"android"):ResourceIdentity["provider"];inspect(effect:Effect,signal:AbortSignal):Promise<ProviderObservation>;launchInert(effect:Effect,signal:AbortSignal):Promise<ProviderObservation>;stop(effect:Effect,signal:AbortSignal):Promise<ProviderObservation>}
export class UnavailableProvider implements Provider {
  readonly available=false;kind():"unavailable"{return "unavailable";}
  async inspect():Promise<never>{throw new Error("provider_unavailable");}
  async launchInert():Promise<never>{throw new Error("provider_unavailable");}
  async stop():Promise<never>{throw new Error("provider_unavailable");}
}
export interface ObjectVerifier {verify(request:WireRequest,result:BuildResult,attestationSha256:string):Promise<boolean>}
export class UnavailableObjectVerifier implements ObjectVerifier {async verify():Promise<boolean>{return false;}}
