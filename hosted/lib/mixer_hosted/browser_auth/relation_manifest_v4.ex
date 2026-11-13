defmodule MixerHosted.BrowserAuth.RelationManifestV4 do
  @moduledoc false
  alias MixerHosted.BrowserAuth.RelationManifestV3
  @creator_relations ~w(public.mixer_authz_bindings public.mixer_authz_credentials
    public.mixer_authz_families public.mixer_authz_principals public.mixer_authz_profiles)

  def for_major(major), do: RelationManifestV3.for_major(major)

  def acl_rows(catalog_oid, creator_oid, owner_oid) do
    RelationManifestV3.acl_rows(catalog_oid, owner_oid) ++
      Enum.map(@creator_relations, fn relation ->
        %{
          "relation" => relation,
          "column" => nil,
          "null" => false,
          "grantee" => creator_oid,
          "grantor" => owner_oid,
          "privilege" => "SELECT",
          "option" => false
        }
      end)
  end
end
