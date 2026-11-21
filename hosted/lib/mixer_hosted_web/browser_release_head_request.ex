defmodule MixerHostedWeb.BrowserReleaseHeadRequest do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Releases.Target

  @fields ~w(organization_id project_id application_id environment_id platform runtime_fingerprint channel)
  @selection_fields @fields ++ ~w(sequence manifest_sha256)

  def parse(raw) when is_binary(raw) and byte_size(raw) in 1..1024 do
    with pairs <- :binary.split(raw, "&", [:global]),
         true <- length(pairs) in [7, 8, 10],
         {:ok, fields} <- Enum.reduce_while(pairs, {:ok, %{}}, &add_field/2),
         {:ok, target} <- target(fields),
         {:ok, view} <- view(fields) do
      {:ok, target, view}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def parse(_), do: {:error, :invalid_request}

  defp target(fields) do
    Target.new(%Target{
      scope: %Scope{
        organization_id: fields["organization_id"],
        project_id: fields["project_id"],
        application_id: fields["application_id"],
        environment_id: fields["environment_id"]
      },
      platform: fields["platform"],
      runtime_sha256: fields["runtime_fingerprint"],
      channel: fields["channel"]
    })
  end

  defp view(%{"view" => :promotion_group, "sequence" => raw, "manifest_sha256" => digest})
       when byte_size(raw) in 1..20 do
    with {sequence, ""} when sequence > 0 <- Integer.parse(raw),
         true <- ArtifactV3Policy.uint?(sequence) and Integer.to_string(sequence) == raw,
         true <- ArtifactV3Policy.digest?(digest) do
      {:ok, {:promotion_group, sequence, digest}}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp view(fields) do
    if Map.has_key?(fields, "sequence") or Map.has_key?(fields, "manifest_sha256") or
         fields["view"] == :promotion_group do
      {:error, :invalid_request}
    else
      {:ok, Map.get(fields, "view", :summary)}
    end
  end

  # All values in this contract are URL-safe ASCII. The console sends them verbatim.
  defp add_field(pair, {:ok, fields}) do
    case :binary.split(pair, "=") do
      ["view", "details"] when not is_map_key(fields, "view") ->
        {:cont, {:ok, Map.put(fields, "view", :details)}}

      ["view", "details-v2"] when not is_map_key(fields, "view") ->
        {:cont, {:ok, Map.put(fields, "view", :details_v2)}}

      ["view", "promotion-group"] when not is_map_key(fields, "view") ->
        {:cont, {:ok, Map.put(fields, "view", :promotion_group)}}

      [name, value] when name in @selection_fields and not is_map_key(fields, name) ->
        {:cont, {:ok, Map.put(fields, name, value)}}

      _ ->
        {:halt, {:error, :invalid_request}}
    end
  end
end
