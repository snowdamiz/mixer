export interface Interval {
    lowerUs: bigint;
    upperUs: bigint;
    qualificationId: string;
}
export interface Clock {
    sample(): Interval | null;
}
export declare class UnavailableClock implements Clock {
    sample(): null;
}
export declare function validInterval(i: Interval | null): i is Interval;
