defmodule MixerHosted.BrowserAuth.RelationManifest do
  @moduledoc false
  @root Path.expand("../../..", __DIR__)
  @resources for major <- [16, 17],
                 do: Path.join(@root, "priv/browser_auth/relation_surface_v1_pg#{major}.json")
  for path <- @resources, do: @external_resource(path)

  @expected_hashes %{
    16 => "1cefad1ca72c6d904e52db31e3cdc025f0a4a646b44e25357cd043c930481b3b",
    17 => "0b5aca632beed0cede1a83c35095a0f7f0a75de781b7a312f37da056d1d3f83f"
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
