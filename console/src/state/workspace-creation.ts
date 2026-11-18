import { createEffect, createSignal, on, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import { WorkspaceClientError } from "../api/workspace-transport.js";
import type { CreatedWorkspace, WorkspaceCreateClient, WorkspaceCreateInput } from "../api/cookie-workspace-create-client.js";
import { isWorkspaceCreateName, resolveWorkspaceDirectory } from "../domain/workspace-directory.js";
import type { WorkspaceSession } from "./workspace-controller.js";
import type { WorkspaceBinding } from "./workspace-binding.js";

export type WorkspaceCreationSession = WorkspaceSession & { readonly workspaceCreate?: WorkspaceCreateClient };
type ReadySession = Extract<WorkspaceCreationSession, { readonly kind: "ready" }>;
type Submission =
  | { readonly kind: "pending"; readonly input: WorkspaceCreateInput }
  | { readonly kind: "committed"; readonly input: WorkspaceCreateInput; readonly selected: boolean }
  | { readonly kind: "error"; readonly input: WorkspaceCreateInput; readonly message: string };

function message(error: unknown): string {
  if (error instanceof WorkspaceClientError) {
    switch (error.code) {
      case "invalid_request": return "The server refused this name. Enter a valid name.";
      case "permission_denied": return "This session does not have permission to create this workspace item.";
      case "not_found": return "The organization is no longer available.";
      case "quota_exceeded": return "This organization has reached its project limit.";
      case "conflict": return "The server refused this request because the workspace changed.";
    }
  }
  return "Creation could not be confirmed. Check the directory before trying again.";
}

export function createWorkspaceCreation(session: Accessor<WorkspaceCreationSession | undefined>, directory: WorkspaceBinding) {
  const [last, setLast] = createSignal<{ readonly owner: ReadySession; readonly submission: Submission }>();
  let disposed = false;
  let active: { readonly owner: ReadySession; readonly controller: AbortController } | undefined;
  function cancel(): void {
    const previous = active;
    active = undefined;
    previous?.controller.abort();
  }
  createEffect(on(session, value => {
    if (active && active.owner !== value) cancel();
    setLast(previous => previous?.owner === value ? previous : undefined);
  }));
  onCleanup(() => { disposed = true; cancel(); });
  const owner = () => {
    const value = session();
    return !disposed && value?.kind === "ready" && value.workspaceCreate ? value : undefined;
  };
  const state = () => {
    const value = last();
    return value?.owner === owner() ? value?.submission : undefined;
  };
  const canCreateOrganization = () => owner() !== undefined && directory.state().organizations.kind === "ready";
  const ownedOrganization = () => {
    if (!canCreateOrganization()) return undefined;
    const row = resolveWorkspaceDirectory(directory.state()).selectedOrganization;
    return row?.organization_roles.includes("owner") ? row : undefined;
  };
  async function submit(input: WorkspaceCreateInput): Promise<boolean> {
    const current = owner();
    const client = current?.workspaceCreate;
    if (!current || !client || state()?.kind === "pending" || !canCreateOrganization() ||
      !isWorkspaceCreateName(input.displayName) ||
      (input.kind === "project" && ownedOrganization()?.id !== input.organizationId)) return false;
    const refreshCreated = directory.prepareCreatedRefresh();
    const captured = Object.freeze({ ...input });
    const attempt = { owner: current, controller: new AbortController() };
    active = attempt;
    setLast({ owner: current, submission: { kind: "pending", input: captured } });
    try {
      if (owner() !== current) return false;
      let created: CreatedWorkspace;
      try { created = await client.submit(captured, attempt.controller.signal); }
      catch (error) {
        if (owner() === current) setLast({ owner: current, submission: { kind: "error", input: captured, message: message(error) } });
        return false;
      }
      if (owner() !== current) return false;
      const selected = await refreshCreated(created);
      if (owner() !== current) return false;
      setLast({ owner: current, submission: { kind: "committed", input: captured, selected } });
      return true;
    } finally {
      if (active === attempt) active = undefined;
    }
  }
  return Object.freeze({ state, canCreateOrganization, ownedOrganization, submit });
}
