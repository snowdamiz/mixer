alias MixerHosted.Builds.WorkerWire
Code.require_file(Path.join(__DIR__, "candidate/test/support/worker_tls_fixture.ex"))
alias MixerHosted.Test.WorkerData

config = %{
  environment_id: "development",
  pool_id: "native",
  controller_id: "controller-1",
  platforms: [:ios]
}

vectors =
  for text <- ["ascii", "λ", "👩‍💻", "a\u2028b", "a\tb", "a\nb", "a\\\"b", "e\u0301", "é"],
      fence <- [1, 9_007_199_254_740_992, 9_007_199_254_740_993, 9_223_372_036_854_775_807] do
    original = WorkerData.request()
    ref = %{original.ref | organization_id: text, fence: fence}
    spec = %{original.spec | organization_id: text}

    id =
      :crypto.hash(
        :sha256,
        Jason.encode!([
          "mixer-build-operation-v1",
          original.guard.record_id,
          ref.organization_id,
          ref.project_id,
          ref.application_id,
          ref.build_id,
          "ios",
          ref.attempt,
          fence
        ])
      )
      |> Base.encode16(case: :lower)

    request = %{original | operation_id: id, ref: ref, spec: spec}
    {:ok, bytes, _} = WorkerWire.encode(:query, request, config)
    Jason.decode!(bytes)
  end

File.write!(
  Path.join(__DIR__, "cross-runtime-vectors.json"),
  Jason.encode!(%{schema: 1, vectors: vectors}, pretty: true) <> "\n"
)

IO.puts(Jason.encode!(%{vectors: length(vectors), scope: "synthetic-wire-byte-vectors-only"}))
