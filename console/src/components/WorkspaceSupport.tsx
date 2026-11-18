import { createResource, createSignal, For, onCleanup, Show } from "solid-js";
import { validSupportText } from "../api/cookie-workspace-support-client.js";
import type { SupportDraft, WorkspaceSupportClient } from "../api/cookie-workspace-support-client.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";

type WorkspaceSupportProps = {
  readonly client: WorkspaceSupportClient;
  readonly organizationId: string;
};

export function WorkspaceSupport(props: WorkspaceSupportProps) {
  const [opened, setOpened] = createSignal(false);

  return <section class="workspace-current-selection" aria-label="Support">
    <h2>Support</h2>
    <Show when={opened()} fallback={
      <button class="workspace-page-button" type="button" onClick={() => setOpened(true)}>Open support</button>
    }>
      <SupportForm {...props} />
    </Show>
  </section>;
}

function SupportForm(props: WorkspaceSupportProps) {
  const lifetime = new AbortController();
  onCleanup(() => lifetime.abort());

  const [subject, setSubject] = createSignal("");
  const [message, setMessage] = createSignal("");
  const [pending, setPending] = createSignal(false);
  const [confirmation, setConfirmation] = createSignal("");
  const [error, setError] = createSignal("");
  let draft: SupportDraft | undefined;

  const [history, { refetch }] = createResource(async () => {
    try {
      return { kind: "loaded", requests: await props.client.list(props.organizationId, lifetime.signal) } as const;
    } catch {
      return { kind: "failed" } as const;
    }
  });

  async function submit() {
    if (pending()) return;
    setError("");
    setConfirmation("");
    const title = subject().trim();
    const detail = message().trim();
    if (!validSupportText(title, detail)) {
      setError("Enter a subject and message. Shorten either field if it exceeds its limit.");
      return;
    }
    setPending(true);
    try {
      if (draft?.subject !== title || draft.message !== detail) {
        draft = { id: crypto.randomUUID(), subject: title, message: detail };
      }
      const saved = await props.client.submit(props.organizationId, draft, lifetime.signal);
      if (lifetime.signal.aborted) return;
      draft = undefined;
      setSubject("");
      setMessage("");
      setConfirmation(`Request submitted. Reference ${saved.id}.`);
      void refetch();
    } catch (failure) {
      if (lifetime.signal.aborted) return;
      setError(failure instanceof WorkspaceClientError && failure.code === "quota_exceeded"
        ? "You’ve reached the daily support request limit for this organization. Try again later."
        : "Couldn’t confirm your request. You can retry with the same subject and message.");
    } finally {
      if (!lifetime.signal.aborted) setPending(false);
    }
  }

  return <>
    <form class="workspace-create-form" onSubmit={event => {
      event.preventDefault();
      void submit();
    }}>
      <label for="support-subject">Subject</label>
      <input id="support-subject" required maxlength={120} disabled={pending()}
        value={subject()} onInput={event => setSubject(event.currentTarget.value)} />
      <label for="support-message">Message</label>
      <textarea id="support-message" required maxlength={1800} rows={5} disabled={pending()}
        value={message()} onInput={event => setMessage(event.currentTarget.value)} />
      <p>Describe the issue and steps to reproduce it. Leave out passwords, tokens, and signing keys.</p>
      <button class="workspace-page-button" type="submit" disabled={pending()}>
        {pending() ? "Submitting…" : "Submit support request"}
      </button>
    </form>
    <Show when={confirmation()}><p role="status">{confirmation()}</p></Show>
    <Show when={error()}><p role="alert">{error()}</p></Show>
    <h3>Your recent requests</h3>
    <Show when={history.loading}><p role="status">Loading support requests…</p></Show>
    <Show when={history()?.kind === "failed"}>
      <p role="alert">Couldn’t load your support requests.</p>
      <button class="workspace-page-button" type="button" disabled={history.loading}
        onClick={() => void refetch()}>Retry loading requests</button>
    </Show>
    <Show when={history()} keyed>{result => result.kind === "loaded" &&
      <Show when={result.requests.length > 0} fallback={<p>No support requests yet.</p>}>
        <ul>
          <For each={result.requests}>{request => <li>
            <strong><bdi>{request.subject}</bdi></strong>
            <p>Submitted <time dateTime={new Date(request.submitted_at * 1000).toISOString()}>
              {new Date(request.submitted_at * 1000).toLocaleString()}
            </time></p>
            <p>Reference {request.id}</p>
            <p style={{ "white-space": "pre-wrap", "overflow-wrap": "anywhere" }}><bdi>{request.message}</bdi></p>
          </li>}</For>
        </ul>
      </Show>
    }</Show>
  </>;
}
