defmodule MixerHosted.CustomerBuilds.Selection do
  @moduledoc "Exact immutable equality filters. This value grants no authority."
  @fields ~w(organization_id project_id application_id build_id platform source_sha256 toolchain_lock_sha256 build_definition_sha256)a
  @enforce_keys @fields
  defstruct @fields

  def new(value) when is_map(value) and not is_struct(value) do
    if Enum.sort(Map.keys(value)) == Enum.sort(@fields) and
         Enum.all?(~w(organization_id project_id application_id build_id)a, &id?(value[&1])) and
         value.platform in ["ios", "android"] and
         Enum.all?(
           ~w(source_sha256 toolchain_lock_sha256 build_definition_sha256)a,
           &digest?(value[&1])
         ) do
      {:ok, struct!(__MODULE__, value)}
    else
      {:error, :invalid_request}
    end
  end

  def new(%__MODULE__{} = value), do: value |> Map.from_struct() |> new()
  def new(_), do: {:error, :invalid_request}

  def id?(v) when is_binary(v) and byte_size(v) in 1..128,
    do:
      Enum.all?(
        :binary.bin_to_list(v),
        &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in [?., ?_, ?-])
      )

  def id?(_), do: false

  def digest?(v) when is_binary(v) and byte_size(v) == 64,
    do: Enum.all?(:binary.bin_to_list(v), &(&1 in ?0..?9 or &1 in ?a..?f))

  def digest?(_), do: false
end
