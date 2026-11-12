defmodule MixerHosted.CustomerBuildCatalog.Snapshot do
  @moduledoc false
  alias MixerHosted.CustomerBuildCatalog.Input
  alias MixerHosted.CustomerBuilds.{Selection, Snapshot}
  alias MixerHosted.Builds.Journal

  @row ~w(organization_id project_id application_id build_id platform request_key revision journal)a

  def project(input, evidence) do
    rows = evidence["records"]
    true = is_list(rows) and length(rows) <= 26
    keys = Enum.map(rows, &key(input.kind, &1))
    true = keys == Enum.sort(keys) and length(keys) == length(Enum.uniq(keys))
    true = is_nil(input.last) or Enum.all?(keys, &(&1 > input.last))
    # Validate lookahead too: corruption never silently disappears at a page boundary.
    projected = Enum.map(rows, &row!(input, &1))
    page = Enum.take(projected, 25)

    next =
      if length(rows) == 26,
        do: Input.cursor(input.kind, input.scope, Enum.at(keys, 24)),
        else: nil

    parent = %{
      organizationId: input.scope.organization_id,
      projectId: input.scope.project_id,
      nextCursor: next
    }

    {:ok,
     if(input.kind == :applications,
       do: Map.put(parent, :applications, page),
       else: Map.merge(parent, %{applicationId: input.scope.application_id, builds: page})
     )}
  rescue
    _ -> {:error, :storage_unavailable}
  end

  defp key(:applications, r), do: [r["id"]]
  defp key(:builds, r), do: [r["build_id"], r["platform"]]

  defp row!(%{kind: :applications, scope: scope}, r) do
    true =
      r["organization_id"] == scope.organization_id and r["project_id"] == scope.project_id and
        r["active"] === true and Selection.id?(r["id"])

    %{applicationId: r["id"]}
  end

  defp row!(%{kind: :builds, scope: scope}, r) do
    record = Map.new(@row, &{&1, Map.fetch!(r, Atom.to_string(&1))})
    true = Map.take(record, Map.keys(scope)) == scope
    {:ok, build} = Journal.restore(record.journal)

    selection =
      Map.take(record, ~w(organization_id project_id application_id build_id platform)a)
      |> Map.merge(%{
        source_sha256: build.spec.source.sha256,
        toolchain_lock_sha256: build.spec.toolchain_lock_sha256,
        build_definition_sha256: build.spec.build_definition_sha256
      })

    {:ok, dto} = Snapshot.project(record, selection)
    dto
  end
end
