defmodule MixerHosted.CustomerBuildCatalog.Input do
  @moduledoc "Closed fixed-page inputs. Continuations carry data and no authority."
  alias MixerHosted.CustomerBuilds.Selection

  def new(kind, scope, page)
      when kind in [:applications, :builds] and is_map(scope) and not is_struct(scope) and
             is_map(page) and not is_struct(page) do
    fields =
      if kind == :applications,
        do: [:organization_id, :project_id],
        else: [:organization_id, :project_id, :application_id]

    with true <- Enum.sort(Map.keys(scope)) == Enum.sort(fields),
         true <- Enum.all?(fields, &Selection.id?(scope[&1])),
         true <- Map.keys(page) == [:cursor],
         {:ok, last} <- decode(kind, scope, page.cursor) do
      {:ok, %{kind: kind, scope: scope, last: last}}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def new(_, _, _), do: {:error, :invalid_request}

  def cursor(kind, scope, last) do
    kind |> bytes(scope, last) |> Base.url_encode64(padding: false)
  end

  defp decode(_, _, nil), do: {:ok, nil}

  defp decode(kind, scope, value) when is_binary(value) and byte_size(value) in 1..1400 do
    with {:ok, raw} <- Base.url_decode64(value, padding: false),
         true <- byte_size(raw) <= 1024,
         {:ok, parsed} when is_map(parsed) <- Jason.decode(raw),
         last =
           if(kind == :applications,
             do: [parsed["lastApplicationId"]],
             else: [parsed["lastBuildId"], parsed["lastPlatform"]]
           ),
         true <- valid_last?(kind, last),
         ^raw <- bytes(kind, scope, last),
         ^value <- Base.url_encode64(raw, padding: false) do
      {:ok, last}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp decode(_, _, _), do: {:error, :invalid_request}
  defp valid_last?(:applications, [id]), do: Selection.id?(id)

  defp valid_last?(:builds, [id, platform]),
    do: Selection.id?(id) and platform in ["ios", "android"]

  defp bytes(kind, scope, last) do
    parents = [
      {"v", 1},
      {"kind", Atom.to_string(kind)},
      {"organizationId", scope.organization_id},
      {"projectId", scope.project_id}
    ]

    pairs =
      case {kind, last} do
        {:applications, [id]} ->
          parents ++ [{"lastApplicationId", id}]

        {:builds, [id, platform]} ->
          parents ++
            [
              {"applicationId", scope.application_id},
              {"lastBuildId", id},
              {"lastPlatform", platform}
            ]
      end

    "{" <>
      Enum.map_join(pairs, ",", fn {k, v} -> Jason.encode!(k) <> ":" <> Jason.encode!(v) end) <>
      "}"
  end
end
