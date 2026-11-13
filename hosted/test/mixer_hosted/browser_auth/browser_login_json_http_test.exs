Code.require_file("storage_fixture.exs", __DIR__)

defmodule MixerHosted.BrowserAuth.BrowserLoginJSONHTTPTest do
  use ExUnit.Case, async: false
  import MixerHosted.Test.OrdinaryBrowserStartupFixture
  alias MixerHosted.Test.OrdinaryBrowserStartupFixture, as: Fixture
  alias MixerHosted.BrowserAuth.Protocol

  setup_all do
    key = "MIXER_BROWSER_CATALOG_FIXTURE_ROOT"
    parent = System.fetch_env!(key)
    root = Path.join(parent, "browser-login-json-http")
    :ok = File.mkdir(root)
    System.put_env(key, root)
    on_exit(fn -> System.put_env(key, parent) end)
    Fixture.prepare!()
  end

  setup c do
    c |> Fixture.start!() |> Map.take([:root, :http_port])
  end

  test "exact JSON login uses trusted runtime URL and preserves refusal boundaries", c do
    p = bootstrap_http(c)

    hs =
      headers(p.cookie) ++
        [
          {"origin", c.config.public_origin},
          {"x-mixer-csrf", p.csrf},
          {"accept", "application/json"}
        ]

    json_login = http(c, "/auth/login", hs, "POST")
    assert json_login.status == 200
    assert response_header(json_login, "location") == []
    assert response_header(json_login, "cache-control") == ["no-store"]
    assert response_header(json_login, "referrer-policy") == ["no-referrer"]
    assert response_header(json_login, "content-type") == ["application/json; charset=utf-8"]
    envelope = Jason.decode!(json_login.body)
    assert Enum.sort(Map.keys(envelope)) == ["authorization_url", "expires_at"]

    assert is_integer(envelope["expires_at"]) and
             envelope["expires_at"] > System.system_time(:second)

    uri = URI.parse(envelope["authorization_url"])
    assert uri.scheme <> "://" <> uri.host <> uri.path == c.config.authorization_endpoint
    assert URI.decode_query(uri.query)["code_challenge_method"] == "S256"

    for {path, headers} <- [
          {"/auth/login?provider=other", hs},
          {"/auth/login", hs ++ [{"accept", "application/json"}]},
          {"/auth/login", hs ++ [{"origin", c.config.public_origin}]},
          {"/auth/login", hs ++ [{"x-mixer-csrf", p.csrf}]},
          {"/auth/login", List.keyreplace(hs, "x-mixer-csrf", 0, {"x-mixer-csrf", "bad"})},
          {"/auth/login", List.keyreplace(hs, "origin", 0, {"origin", "https://wrong.invalid"})}
        ] do
      refusal = http(c, path, headers, "POST")
      assert refusal.status == 503
      assert response_header(refusal, "location") == []
    end

    leases_clean()
  end

  test "raw HTTP duplicates bodies origins arbitrary inputs and aliases fail closed", c do
    p = bootstrap_http(c)
    h = headers(p.cookie)
    hs = h ++ [{"origin", c.config.public_origin}, {"x-mixer-csrf", p.csrf}]
    before = GenServer.call(c.provider, :count)

    for bad <- [
          h,
          hs ++ h,
          hs ++ [{"Origin", c.config.public_origin}],
          hs ++ [{"X-Mixer-CSRF", p.csrf}],
          hs ++ [{"authorization", "Bearer refused"}],
          h ++ [{"origin", "https://evil.invalid"}, {"x-mixer-csrf", p.csrf}]
        ] do
      r = http(c, "/auth/login", bad, "POST")
      assert r.status == 503
      assert response_header(r, "set-cookie") == [] and response_header(r, "location") == []
    end

    for query <- [
          "?redirect_uri=https://evil.invalid",
          "?tenant=org-b",
          "?token=caller",
          "?return_to=/evil"
        ] do
      assert http(c, "/auth/login" <> query, hs, "POST").status == 503
    end

    assert http(c, "/auth/login", hs ++ [{"content-length", "1"}], "POST", "x").status == 503

    for path <- ["/auth/login/", "/auth/%6cogin", "/AUTH/login", "/auth/logout"] do
      assert http(c, path, hs, "POST").status == 404
    end

    l = begin_http(c, p)
    state = URI.decode_query(l.query)["state"]

    for query <- [
          l.query <> "&state=" <> state,
          l.query <> "&code=duplicate",
          l.query <> "&%73tate=" <> state,
          l.query <> "&tenant=org-b",
          String.replace(l.query, "state=" <> state, "state=" <> Protocol.random_token())
        ] do
      r = http(c, "/auth/callback?" <> query, h)
      assert r.status == 503
      assert response_header(r, "set-cookie") == []
    end

    assert http(c, "/auth/callback?" <> l.query, h ++ h).status == 503

    assert http(c, "/auth/callback?" <> l.query, h ++ [{"content-length", "1"}], "GET", "x").status ==
             503

    assert GenServer.call(c.provider, :count) == before
    assert http(c, "/auth/callback?" <> l.query, h).status == 303
    leases_clean()

    IO.puts(
      "R686_BOUNDARIES duplicate_headers_query=true csrf_origin=true aliases_caller_choices_body_refused=true"
    )
  end
end
