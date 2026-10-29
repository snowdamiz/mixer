// PREPARATION ONLY. No connector call or consumer invocation is authorized here.
// Expected ambient bindings: fs = node:fs/promises; crypto = node:resumeCrypto20261029.
// Never serialize the signed URL or retained Response/controller/reader objects.
var packageArtifactTransferStateR194 = null;
var packageArtifactConsumerR194 = async function packageArtifactConsumerR194(signedUrl, destination) {
  const expectedDirectory = "/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-package-runtime-actual-review/local";
  if (typeof signedUrl !== "string" || !signedUrl.startsWith("https://") ||
      destination !== expectedDirectory) throw new Error("unselected consumer arguments");
  const expectedLength = 1530579;
  const expectedSha256 = "8e3665a6acb472f1ccbbb06eae0a582d5970fa17efdddecb28be405ed7e2c8eb";
  const byteCap = 8388608;
  const timeoutMs = 20000;
  const state = {
    controller: new AbortController(), response: null, reader: null, timer: null,
    eof: false, timeoutFired: false, cancellationResolved: false,
    readerReleased: false, phase: "initializing"
  };
  packageArtifactTransferStateR194 = state;
  const report = {
    schema: 1, status: "in-progress-one-bounded-consumer",
    run_id: 40895131023, run_attempt: 1, artifact_id: 12907091274,
    expected_bytes: expectedLength, expected_sha256: expectedSha256,
    cap_bytes: byteCap, transfer_deadline_ms: timeoutMs,
    consumer_transfers: 1, retries: 0, connector_calls_in_this_source: 0,
    response_or_signed_url_retained_in_receipt: false,
    transport_eof_independently_confirmed: false,
    transfer_deadline_scope: "Fetch, body reads and awaited cancellation use one 20-second deadline. File writes are separate local data operations."
  };
  let chunks = [];
  let total = 0;
  let verifiedBytes = null;
  let failure = null;
  let rejectDeadline = null;
  const deadline = new Promise((resolve, reject) => { rejectDeadline = reject; });
  // Attach a handler immediately so an abort while local checks run is observed.
  deadline.catch(() => {});
  const bounded = operation => Promise.race([operation, deadline]);
  await resumeFs20261029.mkdir(destination, { recursive: false });
  state.timer = setTimeout(() => {
    state.timeoutFired = true;
    state.controller.abort();
    rejectDeadline(new Error("selected transfer deadline"));
  }, timeoutMs);
  try {
    state.phase = "fetch";
    state.response = await bounded(fetch(signedUrl, {
      signal: state.controller.signal, redirect: "error"
    }));
    report.http_status = state.response.status;
    if (!state.response.ok) throw new Error("HTTP status refused");
    state.phase = "header-validation";
    const announcedLength = state.response.headers.get("content-length");
    report.content_length_matches_expected = announcedLength === "1530579";
    if (announcedLength !== "1530579") throw new Error("exact content-length refused");
    if (expectedLength > byteCap) throw new Error("selected length exceeds byte cap");
    if (!state.response.body) throw new Error("response body absent");
    state.reader = state.response.body.getReader();
    state.phase = "bounded-body-read";
    while (true) {
      const item = await bounded(state.reader.read());
      if (item.done) { state.eof = true; break; }
      if (item.value.byteLength > byteCap - total)
        throw new Error("consumer byte cap exceeded");
      if (item.value.byteLength > expectedLength - total)
        throw new Error("body exceeds exact selected length");
      total += item.value.byteLength;
      chunks.push(Buffer.from(item.value));
    }
    state.phase = "payload-identity";
    if (total !== expectedLength) throw new Error("exact payload length refused");
    verifiedBytes = Buffer.concat(chunks, total);
    const actualSha256 = resumeCrypto20261029.createHash("sha256").update(verifiedBytes).digest("hex");
    report.payload = { bytes: verifiedBytes.length, sha256: actualSha256 };
    if (verifiedBytes.length !== expectedLength || actualSha256 !== expectedSha256)
      throw new Error("exact payload identity refused");
  } catch (error) {
    // Do not serialize error messages, stacks, response objects, or URLs.
    failure = { phase: state.phase, type: error?.name ?? "Error" };
  } finally {
    const cleanup = {
      reader_cancel_attempted: false, body_cancel_attempted: false,
      cancellation_resolved: false, reader_release_attempted: false,
      reader_released: false, failed: false
    };
    try {
      if (state.reader !== null) {
        if (!state.eof) {
          cleanup.reader_cancel_attempted = true;
          await bounded(state.reader.cancel());
          state.cancellationResolved = true;
        }
      } else if (state.response !== null && state.response.body !== null && !state.eof) {
        cleanup.body_cancel_attempted = true;
        await bounded(state.response.body.cancel());
        state.cancellationResolved = true;
      }
    } catch (cleanupError) {
      cleanup.failed = true;
      cleanup.error_type = cleanupError?.name ?? "Error";
      if (!state.controller.signal.aborted) state.controller.abort();
    } finally {
      if (state.reader !== null) {
        cleanup.reader_release_attempted = true;
        try {
          state.reader.releaseLock();
          state.readerReleased = true;
          cleanup.reader_released = true;
        } catch (releaseError) {
          cleanup.failed = true;
          cleanup.release_error_type = releaseError?.name ?? "Error";
          if (!state.controller.signal.aborted) state.controller.abort();
        }
      }
      // If cancellation failed before the deadline, retain the original deadline
      // until it fires. Never disarm it while an uncancelled body remains.
      if (!state.eof && !state.cancellationResolved && state.response !== null &&
          state.response.body !== null && !state.timeoutFired) {
        try { await deadline; } catch (deadlineError) {}
      }
      clearTimeout(state.timer);
      cleanup.cancellation_resolved = state.cancellationResolved;
      cleanup.eof_observed_by_consumer = state.eof;
      cleanup.timeout_fired = state.timeoutFired;
      cleanup.signal_aborted = state.controller.signal.aborted;
      cleanup.independent_transport_eof_confirmed = false;
      report.cleanup = cleanup;
    }
  }
  report.bytes_received = total;
  report.failure = failure;
  if (failure !== null || report.cleanup.failed || !state.eof ||
      !state.readerReleased || verifiedBytes === null) {
    report.status = "consumer-refused-no-retry";
    report.retained_payload = false;
  } else {
    state.phase = "retain-closed-exact-payload";
    await resumeFs20261029.writeFile(destination + "/artifact.zip", verifiedBytes, { flag: "wx" });
    report.status = "exact-root-bound-artifact-retained";
    report.retained_payload = true;
    report.artifact_path = destination + "/artifact.zip";
  }
  state.phase = "receipt";
  await resumeFs20261029.writeFile(destination + "/acquisition.json",
    JSON.stringify(report, null, 2) + "\n", { flag: "wx" });
  return report;
};
