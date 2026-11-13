defmodule MixerHosted.BrowserAuth.StartupSecrets do
  @moduledoc """
  Pure loading of one trusted process-launch injection, bound to configured refs.

  The installation must supply the environment. Struct shape does not attest its
  provenance. No resolver, fallback, generation, rotation or I/O is performed.
  Never log the environment or extracted fields; no memory zeroization is claimed.
  """
  alias MixerHosted.BrowserAuth.{Config, Custody}
  alias MixerHosted.Identity.BoundedJSON

  @derive {Inspect, only: []}
  @enforce_keys [:client_credential, :custody, :lifecycle]
  defstruct @enforce_keys
  @error {:error, :session_unavailable}
  @variable "MIXER_BROWSER_AUTH_SECRET_MATERIAL"

  def load(env, %Config{mode: :configured} = config) when is_map(env) do
    with {:ok, object} <- BoundedJSON.object(Map.get(env, @variable), 16_384),
         true <- exact?(object, ~w(version client session_vault lifecycle)),
         1 <- object["version"],
         client = object["client"],
         true <- exact?(client, ~w(reference value)),
         true <- reference?(config.client_credential_ref, "secret://"),
         true <- client["reference"] === config.client_credential_ref,
         true <- secret?(client["value"]),
         vault = object["session_vault"],
         true <- exact?(vault, ~w(reference key_id key_base64)),
         true <- vault["reference"] === config.session_vault_ref,
         encoded when is_binary(encoded) and byte_size(encoded) == 44 <- vault["key_base64"],
         {:ok, bytes} <- Base.decode64(encoded),
         true <- Base.encode64(bytes) === encoded,
         {:ok, custody} <-
           Custody.new(config.session_vault_ref, %{
             reference: vault["reference"],
             key_id: vault["key_id"],
             key_bytes: bytes
           }),
         lifecycle = object["lifecycle"],
         true <- exact?(lifecycle, ~w(username password writer_role relation_owner)),
         true <- bounded?(lifecycle["password"]),
         roles = Enum.map(~w(username writer_role relation_owner), &lifecycle[&1]),
         true <- Enum.all?(roles, &role?/1) and length(Enum.uniq(roles)) == 3 do
      {:ok,
       %__MODULE__{
         client_credential: %{reference: client["reference"], value: client["value"]},
         custody: custody,
         lifecycle: %{
           username: lifecycle["username"],
           password: lifecycle["password"],
           writer_role: lifecycle["writer_role"],
           relation_owner: lifecycle["relation_owner"]
         }
       }}
    else
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  # Disabled/absent configuration never constructs secret-bearing capabilities.
  def load(_, _), do: @error

  defp exact?(value, keys),
    do:
      is_map(value) and map_size(value) == length(keys) and
        Enum.all?(keys, &Map.has_key?(value, &1))

  defp bounded?(value), do: is_binary(value) and byte_size(value) in 1..4096

  # ProviderHTTPS form-encodes the value before Basic encoding. Refuse header
  # delimiters here too; preserve other admitted UTF-8 bytes without normalization.
  defp secret?(value),
    do:
      bounded?(value) and String.valid?(value) and
        :binary.match(value, [<<0>>, "\r", "\n"]) == :nomatch

  defp role?(name) when is_binary(name) and byte_size(name) in 1..63 do
    name != "public" and not String.starts_with?(name, "pg_") and
      name
      |> :binary.bin_to_list()
      |> Enum.with_index()
      |> Enum.all?(fn {byte, index} ->
        byte in ?a..?z or byte == ?_ or (index > 0 and byte in ?0..?9)
      end)
  end

  defp role?(_), do: false

  defp reference?(value, prefix) when is_binary(value) and byte_size(value) <= 256 do
    if String.starts_with?(value, prefix) do
      rest = binary_part(value, byte_size(prefix), byte_size(value) - byte_size(prefix))

      rest != "" and
        Enum.all?(:binary.split(rest, "/", [:global]), fn segment ->
          segment != "" and segment not in [".", ".."] and
            Enum.all?(:binary.bin_to_list(segment), fn byte ->
              byte in ?a..?z or byte in ?A..?Z or byte in ?0..?9 or byte in ~c"-._"
            end)
        end)
    else
      false
    end
  end

  defp reference?(_, _), do: false
end
