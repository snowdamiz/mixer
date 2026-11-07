defmodule MixerHosted.BrowserAuth.ActivationPreparation do
  @moduledoc """
  Decodes the closed activation-preparation projection into provisional metadata.

  A successful decode proves shape only. It does not establish database
  provenance, freshness, authentication, authorization or a binding to the
  owner-retained claim, current verified identity or configuration. Those
  comparisons belong to the future trusted lifecycle owner. Never log inputs.
  """
  alias MixerHosted.BrowserAuth.StoredSnapshot

  @derive {Inspect, only: []}
  @enforce_keys [
    :version,
    :snapshot,
    :principal_id,
    :profile_revision,
    :binding_revision,
    :principal_revision
  ]
  defstruct @enforce_keys

  @type t :: %__MODULE__{
          version: 1,
          snapshot: %StoredSnapshot{},
          principal_id: String.t(),
          profile_revision: pos_integer(),
          binding_revision: pos_integer(),
          principal_revision: pos_integer()
        }

  @fields ~w(version snapshot principal_id profile_revision binding_revision principal_revision)
  @revision_fields ~w(profile_revision binding_revision principal_revision)
  @max_integer 9_007_199_254_740_991
  @error {:error, :session_unavailable}

  @doc "Validates exactly six string keys and retains the complete claimed StoredSnapshot."
  @spec decode(term()) :: {:ok, t()} | {:error, :session_unavailable}
  def decode(input) do
    with true <- exact?(input),
         1 <- input["version"],
         true <- text?(input["principal_id"]),
         true <- Enum.all?(@revision_fields, &positive?(input[&1])),
         {:ok,
          %StoredSnapshot{attempt: %{"status" => "claimed"}, attempt_envelope: nil} = snapshot} <-
           StoredSnapshot.decode(input["snapshot"]) do
      {:ok,
       %__MODULE__{
         version: 1,
         snapshot: snapshot,
         principal_id: input["principal_id"],
         profile_revision: input["profile_revision"],
         binding_revision: input["binding_revision"],
         principal_revision: input["principal_revision"]
       }}
    else
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  defp exact?(input),
    do:
      is_map(input) and map_size(input) == length(@fields) and
        Enum.all?(@fields, &Map.has_key?(input, &1))

  defp positive?(value), do: is_integer(value) and value in 1..@max_integer

  defp text?(value),
    do:
      is_binary(value) and byte_size(value) in 1..128 and String.valid?(value) and
        :binary.match(value, <<0>>) == :nomatch
end
