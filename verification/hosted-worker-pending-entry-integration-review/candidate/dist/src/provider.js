export class UnavailableProvider {
    available = false;
    kind() { return "unavailable"; }
    async inspect() { throw new Error("provider_unavailable"); }
    async launchInert() { throw new Error("provider_unavailable"); }
    async stop() { throw new Error("provider_unavailable"); }
}
export class UnavailableObjectVerifier {
    async verify() { return false; }
}
