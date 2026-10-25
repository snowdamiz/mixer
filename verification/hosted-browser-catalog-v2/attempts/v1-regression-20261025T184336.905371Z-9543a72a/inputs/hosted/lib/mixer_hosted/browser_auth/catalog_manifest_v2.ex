defmodule MixerHosted.BrowserAuth.CatalogManifestV2 do
  @moduledoc """
  Build-time combined function/type expectation for the preparation addition.

  This does not select a runtime owner, install SQL or admit relations. Source
  pins bind the accepted static producers and decoder; no live catalog data or
  caller-supplied expectation can change this manifest.
  """
  alias MixerHosted.BrowserAuth.{ActivationPreparationSchema, CatalogManifest}

  @source_pins %{
    "storage_schema.ex" => "676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd",
    "catalog_manifest.ex" => "3508c85922a1a716d39eb61ecb5daa699d6141b1aeb88a9565512c78465d1269",
    "activation_preparation_schema.ex" =>
      "d58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8",
    "activation_preparation.ex" =>
      "e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5"
  }
  for {name, expected} <- @source_pins do
    source = Path.expand(name, __DIR__)
    @external_resource source
    actual = :crypto.hash(:sha256, File.read!(source)) |> Base.encode16(case: :lower)
    unless actual == expected, do: raise("reviewed browser v2 source pin mismatch")
  end

  @addition ActivationPreparationSchema.catalog_manifest()
  @name "mixer_browser_prepare_activation"
  @type_name "mixer_browser_access_evidence"
  @signature "bytea,bytea,bytea,bytea,bigint,public.mixer_browser_access_evidence"
  @argument_names ~w(p_cookie p_state p_config p_claim p_revision i)
  @fields [
    {"profile_id", "text"},
    {"profile_version", "integer"},
    {"issuer", "text"},
    {"subject", "text"},
    {"client_id", "text"},
    {"credential_ref", "text"},
    {"issued_at", "bigint"},
    {"expires_at", "bigint"},
    {"scopes", "text[]"}
  ]
  @settings [
    "search_path=pg_catalog",
    "statement_timeout=5s",
    "lock_timeout=500ms",
    "idle_in_transaction_session_timeout=5s",
    "bytea_output=hex"
  ]
  @decoder %{
    module: "MixerHosted.BrowserAuth.ActivationPreparation",
    source_sha256: Map.fetch!(@source_pins, "activation_preparation.ex")
  }
  @function Map.fetch!(@addition.functions, @name)

  unless @addition.version == 2 and @addition.baseline_version == 1 and
           @addition.additive_only == true and @addition.decoder == @decoder and
           Map.keys(@addition.functions) == [@name] and
           @addition.composites == %{@type_name => @fields} and
           @function.signature == @signature and @function.returns == "jsonb" and
           @function.argument_names == @argument_names and @function.settings == @settings and
           @function.security_definer == true and @function.runtime_execute == true and
           is_binary(@function.source) and byte_size(@function.source) in 1..65_536 do
    raise "reviewed browser v2 addition is incomplete"
  end

  @functions Map.merge(CatalogManifest.functions(), @addition.functions)
  @returns Map.put(CatalogManifest.returns(), @name, "jsonb")
  @arguments Map.put(CatalogManifest.argument_names(), @name, @argument_names)
  @composites Map.merge(CatalogManifest.composites(), %{@type_name => @fields})

  unless map_size(CatalogManifest.functions()) == 18 and
           map_size(CatalogManifest.composites()) == 3 and
           not Map.has_key?(CatalogManifest.functions(), @name) and
           not Map.has_key?(CatalogManifest.composites(), @type_name) and
           map_size(@functions) == 19 and map_size(@composites) == 4 and
           Enum.count(@functions, fn {_name, f} -> f.runtime_execute == true end) == 10 and
           Enum.sum(Enum.map(@composites, fn {_name, fields} -> length(fields) end)) == 34 and
           MapSet.new(Map.keys(@functions)) == MapSet.new(Map.keys(@returns)) and
           MapSet.new(Map.keys(@functions)) == MapSet.new(Map.keys(@arguments)) and
           Enum.all?(@functions, fn {_name, f} ->
             is_binary(f.source) and byte_size(f.source) in 1..65_536 and
               is_binary(f.signature) and byte_size(f.signature) in 1..4096 and
               length(String.split(f.signature, ",")) <= 16 and f.settings == @settings and
               f.security_definer == true and is_boolean(f.runtime_execute)
           end) do
    raise "reviewed browser v2 combined surface is incomplete"
  end

  def functions, do: @functions
  def argument_names, do: @arguments
  def returns, do: @returns
  def composites, do: @composites
  def decoder, do: @decoder
  def source_pins, do: @source_pins
end
