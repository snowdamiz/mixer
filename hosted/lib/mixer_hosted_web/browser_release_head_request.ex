defmodule MixerHostedWeb.BrowserReleaseHeadRequest do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Releases.Target

  @fields ~w(organization_id project_id application_id environment_id platform runtime_fingerprint channel)

  def parse(raw) when is_binary(raw) and byte_size(raw) in 1..1024 do
    with pairs <- :binary.split(raw, "&", [:global]),
         true <- length(pairs) == length(@fields),
         {:ok, fields} <- Enum.reduce_while(pairs, {:ok, %{}}, &add_field/2) do
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
    else
      _ -> {:error, :invalid_request}
    end
  end

  def parse(_), do: {:error, :invalid_request}

  # All values in this contract are URL-safe ASCII. The console sends them verbatim.
  defp add_field(pair, {:ok, fields}) do
    case :binary.split(pair, "=") do
      [name, value] when name in @fields and not is_map_key(fields, name) ->
        {:cont, {:ok, Map.put(fields, name, value)}}

      _ ->
        {:halt, {:error, :invalid_request}}
    end
  end
end
