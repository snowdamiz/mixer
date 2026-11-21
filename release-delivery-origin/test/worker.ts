import {isTarget} from "../src/contract.js";
import {applySnapshot, stageArtifact, stageAssignment} from "../src/writer.js";

interface Env {
  DELIVERY_TARGET: string;
  DELIVERY_PUBLIC: R2Bucket;
}

// Miniflare service binding used by the local fixture. The public worker does
// not mount this entry point.
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const target: unknown = JSON.parse(env.DELIVERY_TARGET);
    if (!isTarget(target) || request.method !== "POST") return new Response(null, {status: 400});
    const url = new URL(request.url);
    try {
      switch (url.pathname) {
        case "/assignment":
          return Response.json(await stageAssignment(env.DELIVERY_PUBLIC, target, await request.arrayBuffer()));
        case "/artifact":
          return Response.json(await stageArtifact(env.DELIVERY_PUBLIC, target,
            url.searchParams.get("digest") ?? "", await request.arrayBuffer()));
        case "/snapshot":
          return Response.json(await applySnapshot(env.DELIVERY_PUBLIC, target, await request.arrayBuffer()));
        default:
          return new Response(null, {status: 404});
      }
    } catch (error) {
      return new Response(error instanceof Error ? error.message : "fixture_error", {status: 409});
    }
  },
};
