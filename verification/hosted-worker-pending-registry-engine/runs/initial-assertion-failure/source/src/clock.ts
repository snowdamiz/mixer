import {MAX} from "./wire.js";
export interface Interval {lowerUs:bigint;upperUs:bigint;qualificationId:string}
export interface Clock {sample():Interval|null}
// No wall clock is silently treated as a measured bounded-error time source.
export class UnavailableClock implements Clock {sample():null{return null;}}
export function validInterval(i:Interval|null):i is Interval {
  return !!i&&i.lowerUs>0n&&i.upperUs>=i.lowerUs&&i.upperUs<=MAX&&
    i.upperUs-i.lowerUs<=2_000_000n&&/^[a-zA-Z0-9_-]{1,128}$/.test(i.qualificationId);
}
