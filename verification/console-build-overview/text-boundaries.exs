alias MixerHosted.Builds.Lifecycle

# Original representative vectors arrive as UTF-8 hex, including intentionally
# invalid surrogate byte sequences. Exercise the actual pure constructor.
IO.read(:stdio, :eof)
|> String.split("\n", trim: true)
|> Enum.each(fn line ->
  [index, field, hex] = String.split(line, "\t", parts: 3)
  text = Base.decode16!(hex, case: :lower)
  source = %{kind: :revision, sha256: String.duplicate("a", 64), reference: "main"}
  spec = %{
    organization_id: "organization", project_id: "project", application_id: "application",
    build_id: "build", platform: :ios, source: source,
    toolchain_lock_sha256: String.duplicate("b", 64), build_definition_sha256: String.duplicate("c", 64)
  }
  spec = case field do
    "organizationId" -> %{spec | organization_id: text}
    "projectId" -> %{spec | project_id: text}
    "applicationId" -> %{spec | application_id: text}
    "buildId" -> %{spec | build_id: text}
    "sourceReference" -> %{spec | source: %{source | reference: text}}
  end
  accepted = case Lifecycle.new(spec, %{max_attempts: 3, timeout_ms: 1000, retry_backoff_ms: 0}, "text-boundary", 0) do
    {:ok, _} -> true
    {:error, _} -> false
  end
  IO.puts("#{index}\t#{accepted}")
end)
