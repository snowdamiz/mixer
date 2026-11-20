defmodule MixerHosted.Releases.Target do
  @moduledoc "A release selection. It carries no tenant or signing authority."
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.ArtifactV3Policy

  @enforce_keys [:scope, :platform, :runtime_sha256, :channel]
  defstruct @enforce_keys

  @type t :: %__MODULE__{
          scope: Scope.t(),
          platform: String.t(),
          runtime_sha256: String.t(),
          channel: String.t()
        }

  def new(%__MODULE__{scope: %Scope{} = scope} = target) do
    with {:ok, ^scope} <- Scope.new(scope),
         true <- map_size(target) == 5,
         true <- ArtifactV3Policy.scope?(signed_scope(target)),
         true <- ArtifactV3Policy.digest?(target.runtime_sha256),
         true <- ArtifactV3Policy.id?(target.channel) do
      {:ok, target}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def new(_), do: {:error, :invalid_request}

  def signed_scope(%__MODULE__{scope: scope, platform: platform}) do
    %{
      "organization" => scope.organization_id,
      "project" => scope.project_id,
      "app" => scope.application_id,
      "environment" => scope.environment_id,
      "platform" => platform
    }
  end

  def filter(%__MODULE__{} = target) do
    Map.to_list(Map.from_struct(target.scope)) ++
      [platform: target.platform, runtime_sha256: target.runtime_sha256, channel: target.channel]
  end

  def wire(%__MODULE__{scope: scope} = target) do
    %{
      organizationId: scope.organization_id,
      projectId: scope.project_id,
      applicationId: scope.application_id,
      environmentId: scope.environment_id,
      platform: target.platform,
      runtimeFingerprint: target.runtime_sha256,
      channel: target.channel
    }
  end
end
