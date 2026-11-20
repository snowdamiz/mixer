defmodule MixerHosted.Test.ReleaseHeadBrowserCheckpoint do
  @moduledoc false
  import ExUnit.Assertions
  alias MixerHosted.BrowserAuth.ProviderTLSFixture

  def capture_cookie(mode, response, header) do
    [cookie] = header.(response, "set-cookie")
    Process.put({__MODULE__, mode}, cookie)
  end

  def wait!(phase, c, path, expected, denied \\ nil) do
    root = System.fetch_env!("MIXER_L05_REPLAY")
    snapshot = Path.join(root, "#{phase}.json")

    info = %{
      phoenix: c.http_port,
      provider: c.provider_port,
      jwks: ProviderTLSFixture.info(c.fixture).port,
      path: path,
      expected: expected,
      denied: denied,
      cookies: %{
        owner: Process.get({__MODULE__, :release_cli}),
        other: Process.get({__MODULE__, :other_tenant})
      }
    }

    File.write!(snapshot <> ".tmp", Jason.encode!(info))
    File.rename!(snapshot <> ".tmp", snapshot)
    deadline = System.monotonic_time(:second) + 120

    Stream.repeatedly(fn -> Process.sleep(100) end)
    |> Enum.find(fn _ ->
      assert System.monotonic_time(:second) < deadline, "Browser checkpoint timed out: #{phase}"
      File.exists?(Path.join(root, "#{phase}.complete"))
    end)
  end

  def published!(response, assignment, payload) do
    assert %{
             "kind" => "published",
             "release" => %{
               "releaseId" => assignment["release_id"],
               "sequence" => Integer.to_string(assignment["sequence"]),
               "rolloutBasisPoints" => assignment["rollout_basis_points"],
               "manifestSha256" => assignment["artifact_sha256"],
               "payloadSha256" => :crypto.hash(:sha256, payload) |> Base.encode16(case: :lower)
             }
           } == Map.take(response, ~w(kind release))

    :ok
  end
end
