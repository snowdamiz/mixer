import {type Target, digest, encoder, fresh, id, isTarget, offers, prefix, sha256, targetFields, tenantFields} from "./contract.js";
import {type Reader, current, readArtifact, readAssignment, readyArtifact} from "./storage.js";

interface Env {
  DELIVERY_TARGET: string;
  DELIVERY_PUBLIC: Reader;
}

function response(status: number, body: BodyInit | null = null): Response {
  const headers = new Headers({"Cache-Control": "no-store"});
  if (body !== null) headers.set("Content-Type", "application/json");
  return new Response(body, {status, headers});
}

function query(url: URL, fields: readonly string[]): Record<string, string> | null {
  if (!url.search || url.search.length > 4097 || url.search.slice(1).split("&").length !== fields.length) return null;
  const allowed = new Set(fields);
  const result: Record<string, string> = {};
  for (const [name, value] of url.searchParams) {
    if (!allowed.delete(name) || !id(value)) return null;
    result[name] = value;
  }
  return allowed.size === 0 ? result : null;
}

// release-v3.json defines a canonical CBOR map of these six ASCII text fields.
// In encoded key order, all keys fit in the single-byte CBOR text-length form.
async function cohort(target: Target, installation: string): Promise<number> {
  const pairs: [string, string][] = [["app", target.app], ["channel", target.channel], ["project", target.project],
    ["environment", target.environment], ["installation", installation], ["organization", target.organization]];
  const bytes = [0xa6];
  for (const [key, value] of pairs) {
    bytes.push(0x60 + key.length, ...encoder.encode(key));
    if (value.length < 24) bytes.push(0x60 + value.length);
    else bytes.push(0x78, value.length);
    bytes.push(...encoder.encode(value));
  }
  return Number(BigInt("0x" + await sha256(Uint8Array.from(bytes).buffer)) % 10_000n);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "GET") return response(405);
    if (request.url.length > 4608) return response(400);
    const url = new URL(request.url);
    const update = url.pathname === "/v3/updates";
    const artifactRoute = url.pathname.startsWith("/v3/artifacts/");
    if (!update && !artifactRoute) return response(404);

    try {
      const target: unknown = JSON.parse(env.DELIVERY_TARGET);
      if (!isTarget(target)) return response(503);
      const bucket = env.DELIVERY_PUBLIC;
      if (update) {
        const fields = query(url, [...targetFields, "installation"]);
        if (!fields || fields.installation === undefined) return response(400);
        const {installation, ...requested} = fields;
        if (!isTarget(requested)) return response(400);
        if (prefix(requested) !== prefix(target)) return response(204);
        const state = await current(bucket, target);
        if (!state || !fresh(state.snapshot, Date.now()) || !offers(state.snapshot.head)) return response(204);
        const {snapshot} = state;
        const {head} = snapshot;
        if (await cohort(target, installation) >= head.rollout_basis_points) return response(204);
        const artifact = snapshot.artifacts.find(item => item.manifest_sha256 === head.artifact_sha256);
        if (!artifact || !await readyArtifact(bucket, target, artifact)) return response(503);
        const assignment = await readAssignment(bucket, snapshot);
        if (!fresh(snapshot, Date.now())) return response(204);
        const tenant = new URLSearchParams({organization: target.organization, project: target.project});
        const download = "/v3/artifacts/" + head.artifact_sha256 + "?" + tenant;
        const body = new Blob(['{"signed_assignment":', assignment, ',"artifact_url":', JSON.stringify(download), "}"]);
        return response(200, body);
      }

      const fields = query(url, tenantFields);
      const hash = url.pathname.slice("/v3/artifacts/".length);
      if (!fields || !digest(hash)) return response(400);
      if (fields.organization !== target.organization || fields.project !== target.project) return response(404);
      const state = await current(bucket, target);
      if (!state || !fresh(state.snapshot, Date.now())) return response(404);
      const artifact = state.snapshot.artifacts.find(item => item.manifest_sha256 === hash);
      if (!artifact) return response(404);
      const bytes = await readArtifact(bucket, target, artifact);
      return fresh(state.snapshot, Date.now()) ? response(200, bytes) : response(404);
    } catch {
      return response(503);
    }
  },
};
