defmodule MixerHosted.BrowserAuth.RelationManifest do
  @moduledoc false
  @root Path.expand("../../..", __DIR__)
  @resources for major <- [16, 17],
                 do: Path.join(@root, "priv/browser_auth/relation_surface_v1_pg#{major}.json")
  for path <- @resources, do: @external_resource(path)

  @expected_hashes %{
    16 => "92e7628577883384d7a5eb882223b91d877ef775d1bee18aa25ffac9bc202318",
    17 => "314fdc83420aba815f5c293b39ecbe5c2be55e24303db511c3287892331ec15e"
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
