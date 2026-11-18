import { createSignal } from "solid-js";
import { isWorkspaceCreateName } from "../domain/workspace-directory.js";

export function WorkspaceCreateForm(props: {
  readonly item: "organization" | "project";
  readonly pending: boolean;
  readonly onCreate: (name: string) => Promise<boolean>;
}) {
  const [name, setName] = createSignal("");
  const valid = () => isWorkspaceCreateName(name());
  const noun = () => props.item === "organization" ? "Organization" : "Project";
  return <form class="workspace-create-form" aria-label={`Create ${props.item}`} onSubmit={event => {
    event.preventDefault();
    if (!valid() || props.pending) return;
    void props.onCreate(name()).then(created => { if (created) setName(""); });
  }}>
    <label for={`workspace-create-${props.item}-name`}>{noun()} name</label>
    <div>
      <input id={`workspace-create-${props.item}-name`} name="display_name" type="text" required maxLength={128}
        value={name()} disabled={props.pending} aria-invalid={name() !== "" && !valid()}
        onInput={event => setName(event.currentTarget.value)} />
      <button type="submit" class="workspace-page-button" disabled={props.pending || !valid()}>Create {props.item}</button>
    </div>
    {name() !== "" && !valid() && <p role="alert">Enter a non-blank name of up to 128 UTF-8 bytes.</p>}
  </form>;
}
