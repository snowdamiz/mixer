defmodule MixerHosted.BrowserAuth.RelationManifestV3 do
  @moduledoc false
  alias MixerHosted.BrowserAuth.RelationManifest
  alias MixerHosted.CustomerBuildCatalog.Schema

  # PG16 is intentionally closed until its exact versioned controls execute.
  def for_major(17), do: RelationManifest.for_major(17)
  def for_major(_), do: raise(MixerHosted.BrowserAuth.RelationCatalog.Unavailable)

  def acl_rows(catalog_oid, owner_oid) do
    frozen = RelationManifest.names()

    Schema.surface_contract().grants
    |> Enum.filter(fn {relation, _} -> relation in frozen end)
    |> Enum.map(fn {relation, privilege} ->
      %{
        "relation" => relation,
        "column" => nil,
        "null" => false,
        "grantee" => catalog_oid,
        "grantor" => owner_oid,
        "privilege" => privilege,
        "option" => false
      }
    end)
  end
end
