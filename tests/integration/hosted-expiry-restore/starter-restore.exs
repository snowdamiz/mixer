# Test-only API attachment to an already restored database.
Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.RestoredStarterHTTPTest do
  use ExUnit.Case, async: false

  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.BrowserAuth.RuntimeOwner
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture.Database, as: DB

  @tag timeout: 90_000
  test "attach the ordinary API and sign in using the restored authority rows" do
    assert System.fetch_env!("MIXER_L07_REPLAY") == "restore"
    root = System.fetch_env!("MIXER_L07_ROOT")
    expected = Path.join(root, "pg")
    conn = DB.connection!("browser_admin", "postgres")

    try do
      assert %{rows: [[^expected]]} = Postgrex.query!(conn, "SHOW data_directory", [])
    after
      GenServer.stop(conn)
    end

    c =
      attach_restored_workspace!()
      |> put_in([:hosted, Access.key(:processor_profile)], :builds_v1)
      |> put_in([:hosted, Access.key(:build_cancel)], true)
      |> put_in([:hosted, Access.key(:native)], %{retained_root: Path.join(root, "worker")})
      |> then(fn c ->
        put_in(
          c,
          [:hosted, Access.key(:create_repo)],
          Keyword.put(c.hosted.repo, :username, "mixer_build_create")
        )
      end)
      |> start!()

    assert RuntimeOwner.status().phase == :storage_ready
    assert c.hosted.oban[:queues] == false
    %{rows: [["browser_ordinary", false, false]]} =
      MixerHosted.Repo.query!("""
      SELECT current_user::text, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user
      """)

    owner = login(c)
    :ok = GenServer.call(c.provider, {:subject, "subject-2"})
    outsider = login(c)
    refute owner == outsider

    ready = %{
      port: c.http_port,
      issuerPort: c.provider_port,
      jwksPort: GenServer.call(c.fixture, :authority).port,
      cookie: owner,
      unrelatedCookie: outsider,
      storageReady: true,
      queuesDisabled: true,
      role: "browser_ordinary"
    }

    File.write!(Path.join(root, "api.ready.tmp"), Jason.encode!(ready), [:exclusive])
    File.rename!(Path.join(root, "api.ready.tmp"), Path.join(root, "api.ready"))
    await_stop!(Path.join(root, "api.done"))
  end

  defp login(c) do
    attempt = begin_http(c, bootstrap_http(c))
    callback = http(c, "/auth/callback?" <> attempt.query, attempt.headers)
    assert callback.status == 303
    cookie = response_cookie(callback)
    assert http(c, "/auth/session", headers(cookie)).status == 200
    cookie
  end

  defp await_stop!(path) do
    unless File.regular?(path) do
      Process.sleep(50)
      await_stop!(path)
    end
  end
end
