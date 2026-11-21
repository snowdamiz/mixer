import {DurableObject} from "cloudflare:workers";
import {
  type Target, artifactLimit, assignmentLimit, exact, isSnapshot, isTarget, prefix,
} from "../src/contract.js";
import {type PublicationResult, type ReleaseProjectionSource, publishProjection} from "../src/publisher.js";
import {pointerKey} from "../src/storage.js";

interface Env {
  DELIVERY_TARGET: string;
  DELIVERY_PUBLIC: R2Bucket;
  AUTHORITY: Fetcher;
}

type Projection = NonNullable<Awaited<ReturnType<ReleaseProjectionSource["read"]>>>;
type Authority = Parameters<ReleaseProjectionSource["withCurrent"]>[0];

function bytes(value: unknown, limit: number): ArrayBuffer {
  if (typeof value !== "string" || value.length > Math.ceil(limit / 3) * 4) {
    throw new Error("fixture_bytes");
  }
  const decoded = atob(value);
  if (decoded.length < 1 || decoded.length > limit) throw new Error("fixture_size");
  return Uint8Array.from(decoded, character => character.charCodeAt(0)).buffer;
}

function projection(value: unknown): Projection | null {
  if (value === null) return null;
  if (!exact(value, ["target", "head", "artifacts", "valid_until_unix", "assignment"])) {
    throw new Error("fixture_projection");
  }
  const bound = value.valid_until_unix;
  const {target, head, artifacts, assignment} = value;
  const shape = {version: 1, revision: "1", issued_at_ms: 1, expires_at_ms: 2, target, head, artifacts};
  if (!isSnapshot(shape) || (bound !== null && (typeof bound !== "number" || !Number.isSafeInteger(bound) || bound < 1))) {
    throw new Error("fixture_authority");
  }
  return {
    target: shape.target, head: shape.head, artifacts: shape.artifacts,
    validUntilUnix: bound === null ? null : BigInt(bound),
    assignmentBytes: bytes(assignment, assignmentLimit),
  };
}

function wire(authority: Authority) {
  const {target, head, artifacts, validUntilUnix} = authority;
  return {target, head, artifacts, valid_until_unix: validUntilUnix === null ? null : Number(validUntilUnix)};
}

function isPermit(value: unknown): value is {grant_ms: number; valid_until_unix: number | null} {
  return exact(value, ["grant_ms", "valid_until_unix"])
    && typeof value.grant_ms === "number" && Number.isInteger(value.grant_ms) && value.grant_ms > 0
    && value.grant_ms <= 1000
    && (value.valid_until_unix === null
      || (typeof value.valid_until_unix === "number" && Number.isSafeInteger(value.valid_until_unix)));
}

class Source implements ReleaseProjectionSource {
  constructor(private readonly bridge: Fetcher) {}

  private async call(op: string, args: Record<string, unknown> = {}): Promise<unknown> {
    const response = await this.bridge.fetch("http://authority.invalid/" + op, {
      method: "POST", body: JSON.stringify(args),
    });
    if (!response.ok) throw new Error("fixture_ipc");
    return response.json();
  }

  async read(target: Target): Promise<Projection | null> {
    return projection(await this.call("read", {target}));
  }

  async readArtifact(authority: Authority, artifact: Authority["artifacts"][number]): Promise<ArrayBuffer> {
    return bytes(await this.call("artifact", {authority: wire(authority), artifact}), artifactLimit);
  }

  async withCurrent(
    authority: Authority, publish: (mayWrite: () => boolean) => Promise<PublicationResult>,
  ): Promise<PublicationResult> {
    // Anchor before the round trip. Charging the whole acquisition against the
    // Elixir callback's remaining duration includes the grant's transport time.
    const began = performance.now();
    const wall = Date.now();
    let grant: unknown;
    try {
      grant = await this.call("fence", {authority: wire(authority)});
    } catch {
      return "indeterminate";
    }
    if (!isPermit(grant)) {
      if (exact(grant, ["result"]) && grant.result === "stale") return "stale";
      if (exact(grant, ["result"]) && grant.result === "unavailable") return "unavailable";
      return "indeterminate";
    }

    let mayWrite = grant.valid_until_unix === wire(authority).valid_until_unix;
    const permit = () => {
      const now = Date.now();
      const elapsed = Math.max(performance.now() - began, now - wall);
      mayWrite = mayWrite && now >= wall && elapsed + 5 < grant.grant_ms
        && (grant.valid_until_unix === null || now < grant.valid_until_unix * 1000);
      return mayWrite;
    };
    let result: PublicationResult = "indeterminate";
    try {
      result = await publish(permit);
    } catch {
      // Once the callback is dispatched an R2 exception can be a lost reply.
    }

    try {
      const ack = await this.call("finish", {result});
      if (exact(ack, ["result"])) {
        if (ack.result === "applied" && result === "applied") return result;
        if (ack.result === "retry" && ["expired", "stale", "retry", "unchanged"].includes(result)) return result;
      }
    } catch {
      // The pointer is reconciled by the fixture before any subsequent call.
    }
    return "indeterminate";
  }
}

// Miniflare exposes this fixture-owned binding only through its local proxy.
// No HTTP route invokes the publisher.
export class FixturePublisher extends DurableObject<Env> {
  fetch(): Response {
    return new Response(null, {status: 404});
  }

  async publish(requested: unknown, leaseMs: number, late: boolean) {
    const target: unknown = JSON.parse(this.env.DELIVERY_TARGET);
    if (!isTarget(target) || !isTarget(requested) || prefix(target) !== prefix(requested)) {
      return {result: "unavailable", attempted: null};
    }
    const pointer = pointerKey(target);
    let attempted: string | null = null;
    const bucket = new Proxy(this.env.DELIVERY_PUBLIC, {
      get(native, name) {
        if (name === "put") {
          return async (...args: Parameters<R2Bucket["put"]>) => {
            const [key, value] = args;
            if (late && key.includes("/snapshot/")) await scheduler.wait(1100);
            if (key === pointer && typeof value === "string") attempted = value;
            return native.put(...args);
          };
        }
        const method: unknown = Reflect.get(native, name);
        return typeof method === "function" ? method.bind(native) : method;
      },
    });
    const result = await publishProjection({bucket, target, source: new Source(this.env.AUTHORITY), leaseMs});
    return {result, attempted};
  }
}

export default {
  fetch: () => new Response(null, {status: 404}),
};
