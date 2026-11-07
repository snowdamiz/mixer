defmodule MixerHosted.BrowserAuth.Custody do
  @moduledoc """
  Pure binding of externally supplied browser vault material to its configured reference.

  This constructor does not resolve a reference, generate a key, or establish the
  provenance of supplied material. Secret injection and owner isolation remain
  separate startup responsibilities. Never log the inputs or this struct's fields.
  """
  alias MixerHosted.BrowserAuth.Vault

  @derive {Inspect, only: []}
  @enforce_keys [:reference, :key]
  defstruct @enforce_keys

  @error {:error, :session_unavailable}

  @doc "Binds a canonical vault reference to exactly one externally supplied Vault key."
  def new(reference, %{reference: reference, key_id: id, key_bytes: bytes} = material) do
    with true <- map_size(material) == 3 and reference?(reference),
         {:ok, key} <- Vault.key(id, bytes) do
      {:ok, %__MODULE__{reference: reference, key: key}}
    else
      _ -> @error
    end
  end

  def new(_, _), do: @error

  # This is the same bounded canonical reference grammar admitted by Config.
  defp reference?("vault://" <> rest = reference) when byte_size(reference) <= 256 do
    rest != "" and
      Enum.all?(:binary.split(rest, "/", [:global]), fn segment ->
        segment != "" and segment not in [".", ".."] and
          Enum.all?(:binary.bin_to_list(segment), fn byte ->
            byte in ?a..?z or byte in ?A..?Z or byte in ?0..?9 or byte in ~c"-._"
          end)
      end)
  end

  defp reference?(_), do: false
end
