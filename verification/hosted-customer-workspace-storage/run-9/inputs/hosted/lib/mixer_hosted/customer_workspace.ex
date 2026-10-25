defmodule MixerHosted.CustomerWorkspace do
  @moduledoc """
  Fresh, read-only discovery of a human customer's own workspaces.

  Each call owns its PostgreSQL transaction. Returned descriptive roles are not
  artifact authority. The optional repository is a trusted server/test seam;
  request data never selects it, and no caller callback runs inside this API.
  """

  alias MixerHosted.CustomerWorkspace.{Input, Storage}

  def organizations(identity, page, repo \\ MixerHosted.Repo) do
    with :ok <- Input.identity(identity),
         {:ok, page} <- Input.page(page, "organizations", nil) do
      Storage.read(identity, "organizations", nil, page, repo)
    end
  end

  def projects(identity, organization_id, page, repo \\ MixerHosted.Repo) do
    with :ok <- Input.identity(identity),
         true <- MixerHosted.Authorization.Scope.identifier?(organization_id),
         {:ok, page} <- Input.page(page, "projects", organization_id) do
      Storage.read(identity, "projects", organization_id, page, repo)
    else
      false -> {:error, :invalid_request}
      error -> error
    end
  end
end
