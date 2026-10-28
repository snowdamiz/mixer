defmodule MixerHosted.BrowserAuth.RelationManifest do
  @moduledoc false
  @root Path.expand("../../..", __DIR__)
  @resources for major <- [16, 17],
                 do: Path.join(@root, "priv/browser_auth/relation_surface_v1_pg#{major}.json")
  for path <- @resources, do: @external_resource(path)

  @expected_hashes %{
    16 => "079b8cdeb3c039284b3ae402664230f6abc01782ab5e7f08219a06067e22cadf",
    17 => "100df9346930b778611b46e821484db025671819b3bb966cfcb496014ce42785"
  }
  @manifests Map.new(Enum.zip([16, 17], @resources), fn {major, path} ->
               bytes = File.read!(path)
               digest = :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)

               if digest != Map.fetch!(@expected_hashes, major),
                 do: raise("unreviewed relation manifest")

               {major, Jason.decode!(bytes)}
             end)
  @bindings @manifests[16]["source_bindings"]
  if @bindings != @manifests[17]["source_bindings"], do: raise("relation source binding mismatch")

  for {relative, digest} <- @bindings do
    path = Path.join(Path.dirname(@root), relative)
    @external_resource path
    actual = :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower)
    if actual != digest, do: raise("unreviewed relation source")
  end

  def for_major(major) when major in [16, 17], do: Map.fetch!(@manifests, major)
  def names, do: @manifests[16]["structure"]["relations"] |> Map.keys() |> Enum.sort()
end
