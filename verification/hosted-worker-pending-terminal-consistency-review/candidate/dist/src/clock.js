import { MAX } from "./wire.js";
// No wall clock is silently treated as a measured bounded-error time source.
export class UnavailableClock {
    sample() { return null; }
}
export function validInterval(i) {
    return !!i && i.lowerUs > 0n && i.upperUs >= i.lowerUs && i.upperUs <= MAX &&
        i.upperUs - i.lowerUs <= 2000000n && /^[a-zA-Z0-9_-]{1,128}$/.test(i.qualificationId);
}
