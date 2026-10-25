defmodule MixerHosted.BrowserAuth.RelationManifest do
  @moduledoc false
  @root Path.expand("../../..", __DIR__)
  @resources for major <- [16, 17],
                 do: Path.join(@root, "priv/browser_auth/relation_surface_v1_pg#{major}.json")
  for path <- @resources, do: @external_resource(path)

  @expected_hashes %{
    16 => "f1a64cd89c7e4589cf966849d0c86769870b6c4863a40d1e240d728644f3ed2e",
    17 => "d56f3935138fcb9af8f1c2458c33851146190e5590c5f0896e4bfba58782f366"
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
