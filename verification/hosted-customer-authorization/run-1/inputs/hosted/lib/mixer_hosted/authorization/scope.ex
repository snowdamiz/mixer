defmodule MixerHosted.Authorization.Scope do
  @moduledoc "Bounded tenant ancestry for policy evaluation; a scope grants no authority."

  @fields [:organization_id, :project_id, :application_id, :environment_id]
  @enforce_keys [:organization_id]
  defstruct @fields

  @type t :: %__MODULE__{
          organization_id: binary(),
          project_id: binary() | nil,
          application_id: binary() | nil,
          environment_id: binary() | nil
        }

  @spec new(term()) :: {:ok, t()} | {:error, :invalid_scope}
  def new(%__MODULE__{} = scope) when map_size(scope) == 5,
    do: normalize(Map.from_struct(scope))

  def new(%{} = scope) when not is_struct(scope), do: normalize(scope)
  def new(_), do: {:error, :invalid_scope}

  defp normalize(scope) when map_size(scope) in 1..4 do
    values = Enum.map(@fields, &Map.get(scope, &1))

    if Enum.all?(Map.keys(scope), &(&1 in @fields)) and identifier?(hd(values)) and
         ancestor_path?(values) do
      {:ok, struct!(__MODULE__, scope)}
    else
      {:error, :invalid_scope}
    end
  end

  defp normalize(_), do: {:error, :invalid_scope}

  defp ancestor_path?(values) do
    {present, absent} = Enum.split_while(values, &(not is_nil(&1)))
    Enum.all?(present, &identifier?/1) and Enum.all?(absent, &is_nil/1)
  end

  @doc false
  def identifier?(value),
    do:
      is_binary(value) and byte_size(value) in 1..128 and String.valid?(value) and
        String.printable?(value) and value != "*"

  @doc false
  def project?(%__MODULE__{project_id: project}), do: not is_nil(project)

  @doc false
  def project_only?(%__MODULE__{project_id: project, application_id: nil}),
    do: not is_nil(project)

  @doc false
  def environment?(%__MODULE__{environment_id: environment}), do: not is_nil(environment)

  @doc false
  def membership_covers?(membership, target) do
    source = membership.scope

    source.organization_id == target.organization_id and
      ((source.project_id == nil and membership.project_binding == :all_projects) or
         (source.project_id == target.project_id and
            membership.project_binding == :exact_project))
  end
end
