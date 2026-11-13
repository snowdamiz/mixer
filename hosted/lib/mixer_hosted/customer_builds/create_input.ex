defmodule MixerHosted.CustomerBuilds.CreateInput do
  @moduledoc "Closed customer selection of an immutable server admission."
  @fields ~w(organization_id project_id application_id platform source_input_id source_sha256 toolchain_lock_sha256 build_definition_sha256)a
  @enforce_keys @fields
  defstruct @fields
  def new(%__MODULE__{} = v), do: new(Map.from_struct(v))

  def new(v) when is_map(v) and map_size(v) == 8 do
    if Enum.sort(Map.keys(v)) == Enum.sort(@fields) and
         Enum.all?(
           [:organization_id, :project_id, :application_id, :source_input_id],
           &id?(Map.get(v, &1))
         ) and
         v.platform in [:ios, :android] and
         Enum.all?([:source_sha256, :toolchain_lock_sha256, :build_definition_sha256], fn k ->
           is_binary(v[k]) and Regex.match?(~r/^[0-9a-f]{64}$/, v[k])
         end), do: {:ok, struct!(__MODULE__, v)}, else: {:error, :invalid_request}
  end

  def new(_), do: {:error, :invalid_request}

  def id?(v),
    do: is_binary(v) and byte_size(v) in 1..128 and Regex.match?(~r/^[A-Za-z0-9._-]+$/, v)

  def parse(raw) do
    with {:ok, m} <- MixerHosted.Identity.BoundedJSON.object(raw, 4096),
         true <- Enum.sort(Map.keys(m)) == Enum.sort(Enum.map(@fields, &Atom.to_string/1)),
         p when p in ["ios", "android"] <- m["platform"] do
      new(
        Map.new(@fields, fn k ->
          {k,
           if(k == :platform,
             do: if(p == "ios", do: :ios, else: :android),
             else: m[Atom.to_string(k)]
           )}
        end)
      )
    else
      _ -> {:error, :invalid_request}
    end
  end

  def build_id(v, key) do
    parts = [
      "mixer.customer-build.v1",
      v.organization_id,
      v.project_id,
      v.application_id,
      Atom.to_string(v.platform),
      key
    ]

    bytes = Enum.map(parts, fn p -> <<byte_size(p)::unsigned-big-32, p::binary>> end)
    "build-" <> Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
  end
end

defmodule MixerHosted.CustomerBuilds.CreateRepo do
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end
