import { createSignal, onCleanup, Show } from "solid-js";
import type { RegisterApplication } from "../api/cookie-application-registration-client.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";
import { isBuildCatalogId } from "../domain/build-catalog.js";
import type { ProjectSelection } from "../domain/build-catalog.js";

export function RegisterApplicationForm(props: {
  readonly project: ProjectSelection;
  readonly register: RegisterApplication;
  readonly refresh: () => void;
}) {
  const [id, setId] = createSignal("");
  const [pending, setPending] = createSignal(false);
  const [message, setMessage] = createSignal("");
  const [conflict, setConflict] = createSignal(false);
  const lifetime = new AbortController();
  onCleanup(() => lifetime.abort());

  async function submit() {
    const applicationId = id();
    if (pending() || !isBuildCatalogId(applicationId)) return;
    setPending(true);
    setMessage("");
    setConflict(false);
    try {
      await props.register({ ...props.project, applicationId }, lifetime.signal);
      if (!lifetime.signal.aborted) props.refresh();
    } catch (error) {
      if (lifetime.signal.aborted) return;
      const code = error instanceof WorkspaceClientError ? error.code : undefined;
      if (code === "permission_denied" || code === "not_found") {
        setMessage("Application registration is unavailable for this project.");
      } else if (code === "conflict") {
        setConflict(true);
        setMessage("This project already has an application or the ID is reserved. Refresh the application list before retrying.");
      } else {
        setMessage("Registration could not be confirmed. Retry with the same application ID.");
      }
    } finally {
      if (!lifetime.signal.aborted) setPending(false);
    }
  }

  return <form class="workspace-create-form" aria-label="Register application" onSubmit={event => {
    event.preventDefault();
    void submit();
  }}>
    <label for="register-application-id">Application ID</label>
    <div>
      <input id="register-application-id" name="application_id" type="text" required maxLength={128}
        value={id()} disabled={pending()} aria-describedby="register-application-help"
        aria-invalid={id() !== "" && !isBuildCatalogId(id())}
        onInput={event => { setId(event.currentTarget.value); setMessage(""); setConflict(false); }} />
      <button type="submit" class="workspace-page-button" disabled={pending() || !isBuildCatalogId(id())}>
        Register application
      </button>
    </div>
    <p id="register-application-help">Use up to 128 letters, numbers, periods, underscores, or hyphens.</p>
    <Show when={pending()}><p role="status">Registering application…</p></Show>
    <Show when={conflict()}>
      <button type="button" class="workspace-text-button" onClick={props.refresh}>Refresh applications</button>
    </Show>
    <Show when={message()}>{error => <p role="alert">{error()}</p>}</Show>
  </form>;
}
