defmodule MixerHostedWeb.BearerIdentityTest do
  use ExUnit.Case, async: false

  import Plug.Conn
  import Plug.Test

  alias MixerHosted.Identity.{
    AccessTokenVerifier,
    ConfiguredVerifier,
    TrustSnapshot,
    VerifiedIdentity
  }

  alias MixerHostedWeb.Plugs.BearerIdentity

  @now 1_800_000_000

  defmodule ProbeVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:verification_called, token, now})
      Process.get(:bearer_test_result, {:error, :unauthenticated})
    end
  end

  defmodule SnapshotVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:snapshot_verification_called, token, now})
      AccessTokenVerifier.verify(token, now, Process.get(:bearer_test_snapshot))
    end
  end

  defmodule RaisingVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(_, _), do: raise("private provider response and credential")
  end

  defmodule ThrowingVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(_, _), do: throw({:secret, "private provider response"})
  end

  defmodule ExitingVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(_, _), do: exit(:shutdown)
  end

  def fixed_clock, do: @now
  def bad_clock, do: "not a time"
  def raising_clock, do: raise("private clock details")

  setup_all do
    {:ok, _} = Application.ensure_all_started(:jose)
    private = JOSE.JWK.generate_key({:rsa, 2_048})
    public = private |> JOSE.JWK.to_public() |> JOSE.JWK.to_map() |> elem(1)

    public =
      Map.merge(public, %{
        "kid" => "http-transport-owned-test-key",
        "alg" => "RS256",
        "use" => "sig",
        "key_ops" => ["verify"]
      })

    profile = %{
      profile_id: "http-transport-owned-test-profile",
      profile_version: 1,
      issuer: "https://transport-issuer.invalid/oauth",
      audience: "http-transport-test-api",
      client_id: "http-transport-test-client",
      identity_class: :human,
      enabled: true
    }

    {:ok, snapshot} =
      TrustSnapshot.new(profile, Jason.encode!(%{"keys" => [public]}), @now - 1, @now + 120)

    claims = %{
      "iss" => profile.issuer,
      "aud" => profile.audience,
      "sub" => "synthetic-http-subject",
      "client_id" => profile.client_id,
      "jti" => "synthetic-http-credential",
      "iat" => @now - 10,
      "exp" => @now + 100,
      "scope" => "mixer.artifact.read untrusted.admin",
      "role" => "owner",
      "organization_id" => "not-authority"
    }

    {:ok, private: private, snapshot: snapshot, claims: claims}
  end

  setup do
    Process.put(:bearer_test_result, {:ok, identity()})
    {:ok, opts: options()}
  end

  defp identity do
    %VerifiedIdentity{
      profile_id: "typed-test-profile",
      profile_version: 1,
      issuer: "https://test.invalid/oauth",
      subject: "synthetic-subject",
      client_id: "synthetic-client",
      credential_ref: "synthetic-credential",
      issued_at: @now - 1,
      expires_at: @now + 30,
      identity_class: :human,
      scopes: []
    }
  end

  defp options(overrides \\ []) do
    [verifier: ProbeVerifier, clock: {__MODULE__, :fixed_clock, []}]
    |> Keyword.merge(overrides)
    |> BearerIdentity.init()
  end

  defp request(headers \\ [{"authorization", "Bearer exact.Token-1"}], target \\ "/protected") do
    %{conn(:get, target) | req_headers: headers}
  end

  defp assert_error(conn, status, code, challenge) do
    assert conn.status == status
    assert conn.halted
    refute Map.has_key?(conn.assigns, :verified_identity)
    assert get_resp_header(conn, "cache-control") == ["no-store"]
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
    assert get_resp_header(conn, "www-authenticate") == List.wrap(challenge)
    assert get_resp_header(conn, "retry-after") == if(status == 503, do: ["1"], else: [])
    assert byte_size(conn.resp_body) < 512
    assert %{"error" => error, "request_id" => request_id} = Jason.decode!(conn.resp_body)
    assert Enum.sort(Map.keys(error)) == ["code", "message"]
    assert error["code"] == code
    assert is_binary(error["message"]) and byte_size(error["message"]) < 100
    assert get_resp_header(conn, "x-request-id") == [request_id]
    assert byte_size(request_id) in 20..200
    assert Enum.sort(Map.keys(Jason.decode!(conn.resp_body))) == ["error", "request_id"]
    conn
  end

  defp invalid_request(conn, opts) do
    conn
    |> BearerIdentity.call(opts)
    |> assert_error(400, "invalid_request", ~s(Bearer error="invalid_request"))
  end

  test "missing header is a bare 401 challenge and clears a stale assigned identity", %{
    opts: opts
  } do
    request([])
    |> assign(:verified_identity, identity())
    |> BearerIdentity.call(opts)
    |> assert_error(401, "unauthenticated", "Bearer")

    refute_receive {:verification_called, _, _}
  end

  test "standard scheme casing and one or more spaces preserve exact token bytes", %{opts: opts} do
    for scheme <- ["Bearer", "bearer", "BEARER", "bEaReR"], spaces <- [" ", "   "] do
      token = "aZ09-._~+/=="
      conn = request([{"authorization", scheme <> spaces <> token}]) |> BearerIdentity.call(opts)
      refute conn.halted
      assert conn.assigns == %{verified_identity: identity()}
      assert get_resp_header(conn, "cache-control") == ["no-store"]
      assert_receive {:verification_called, ^token, @now}
    end
  end

  test "4096-byte header and 4089-byte token boundaries are enforced", %{opts: opts} do
    token = String.duplicate("a", 4_089)
    accepted = request([{"authorization", "Bearer " <> token}]) |> BearerIdentity.call(opts)
    refute accepted.halted
    assert_receive {:verification_called, ^token, @now}

    for value <- ["Bearer " <> token <> "a", "Bearer  " <> token] do
      invalid_request(request([{"authorization", value}]), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "duplicate headers reject even if identical or paired with an empty value", %{opts: opts} do
    for values <- [["Bearer a", "Bearer a"], ["Bearer a", "Bearer b"], ["", "Bearer a"]] do
      invalid_request(request(Enum.map(values, &{"authorization", &1})), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "malformed, comma-joined, unsupported and ambiguous schemes reject before verification", %{
    opts: opts
  } do
    for value <- [
          "",
          "Bearer",
          "Bearer ",
          " Bearer abc",
          "Bearer\tabc",
          "Bearer abc ",
          "Bearer abc def",
          "Bearer a,b",
          "Bearer a, Bearer b",
          "Basic abc",
          "Digest abc",
          "Bearer \"abc\"",
          "Bearer =",
          "Bearer abc=def",
          "Bearer abc;def",
          "Bearér abc",
          "Bearer abc:secret",
          "Bearer abc\\def"
        ] do
      invalid_request(request([{"authorization", value}]), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "every ASCII control, DEL, non-ASCII and invalid UTF8 credential is malformed", %{
    opts: opts
  } do
    for byte <- Enum.to_list(0..31) ++ [127, 128, 255] do
      invalid_request(request([{"authorization", "Bearer a" <> <<byte>> <> "b"}]), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "verifier rejection is a generic invalid-token response with no stale identity", %{
    opts: opts
  } do
    Process.put(:bearer_test_result, {:error, :unauthenticated})

    result =
      request()
      |> assign(:verified_identity, identity())
      |> BearerIdentity.call(opts)
      |> assert_error(401, "unauthenticated", ~s(Bearer error="invalid_token"))

    assert_receive {:verification_called, "exact.Token-1", @now}
    refute result.resp_body =~ "exact.Token-1"
    refute result.resp_body =~ "synthetic-subject"
  end

  test "unavailability and unsupported verifier results fail closed without details", %{
    opts: opts
  } do
    for result <- [
          {:error, :identity_unavailable},
          {:error, :rate_limit},
          {:error, "private DSN"},
          {:ok, %{subject: "forged", role: "owner"}},
          {:ok, nil},
          :ok,
          nil,
          {:error, :unauthenticated, "private provider response"}
        ] do
      Process.put(:bearer_test_result, result)

      response =
        request()
        |> assign(:verified_identity, identity())
        |> BearerIdentity.call(opts)
        |> assert_error(503, "identity_unavailable", nil)

      refute response.resp_body =~ "private"
      refute response.resp_body =~ "forged"
      assert_receive {:verification_called, "exact.Token-1", @now}
    end
  end

  test "ordinary adapter exceptions and throws are generic unavailable responses" do
    for verifier <- [RaisingVerifier, ThrowingVerifier] do
      result = request() |> BearerIdentity.call(options(verifier: verifier))
      assert_error(result, 503, "identity_unavailable", nil)
      refute result.resp_body =~ "private"
    end
  end

  test "process exits are not hidden by an all-class catch" do
    assert catch_exit(BearerIdentity.call(request(), options(verifier: ExitingVerifier))) ==
             :shutdown
  end

  test "only a fresh typed result is assigned and HTTP authority assertions are inert", %{
    opts: opts
  } do
    expected = %{identity() | subject: "newly-verified"}
    Process.put(:bearer_test_result, {:ok, expected})

    result =
      request([
        {"authorization", "Bearer a"},
        {"x-role", "owner"},
        {"x-organization-id", "other"}
      ])
      |> assign(:verified_identity, %{identity() | subject: "stale"})
      |> assign(:unrelated, :preserved)
      |> BearerIdentity.call(opts)

    assert result.assigns == %{verified_identity: expected, unrelated: :preserved}
    assert_receive {:verification_called, "a", @now}
    refute result.halted
  end

  test "reserved query token names and bracket forms reject before verifying with or without a header",
       %{opts: opts} do
    for query <- [
          "access_token=a",
          "access_token",
          "%61ccess%5ftoken=a",
          "x=1&access_token=a",
          "access_token[]=a",
          "access_token%5Bvalue%5D=a",
          "access_token=a&access_token=b"
        ],
        headers <- [[], [{"authorization", "Bearer a"}]] do
      invalid_request(request(headers, "/protected?" <> query), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "query names are bounded and malformed or hidden control escapes fail closed", %{
    opts: opts
  } do
    for query <- [
          "%x1=value",
          "%0=value",
          "%00access_token=a",
          "%FF=value",
          "x%7f=value",
          String.duplicate("a", 257) <> "=v",
          Enum.map_join(1..129, "&", fn _ -> "x=v" end),
          "x=" <> String.duplicate("a", 8_191)
        ] do
      invalid_request(request([{"authorization", "Bearer a"}], "/protected?" <> query), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "ordinary query values and fetched params do not provide identity or consume parameters",
       %{opts: opts} do
    raw = "q=access_token%3Da&filter[name]=x&access_token_hint=y&nested[access_token]=z"

    original =
      request([{"authorization", "Bearer a"}], "/protected?" <> raw) |> fetch_query_params()

    result = BearerIdentity.call(original, opts)
    refute result.halted
    assert result.query_string == original.query_string
    assert result.query_params == original.query_params
    assert result.params == original.params
    assert_receive {:verification_called, "a", @now}
  end

  test "query byte, field and decoded-name limits accept their exact boundary", %{opts: opts} do
    for query <- [
          "x=" <> String.duplicate("v", 8_190),
          String.duplicate("a", 256) <> "=v",
          Enum.map_join(1..128, "&", fn _ -> "x=v" end)
        ] do
      result =
        request([{"authorization", "Bearer a"}], "/protected?" <> query)
        |> BearerIdentity.call(opts)

      refute result.halted
      assert_receive {:verification_called, "a", @now}
    end
  end

  test "form bodies are rejected untouched, regardless of token presence or prior parsing", %{
    opts: opts
  } do
    for type <- [
          "application/x-www-form-urlencoded",
          "APPLICATION/X-WWW-FORM-URLENCODED; charset=UTF-8"
        ],
        body <- ["access_token=secret", "ordinary=value"],
        headers <- [[], [{"authorization", "Bearer a"}]] do
      original = conn(:post, "/protected", body)
      original = %{original | req_headers: [{"content-type", type} | headers]}
      result = invalid_request(original, opts)
      assert result.body_params == original.body_params
      assert {:ok, ^body, _} = read_body(result)
      refute_receive {:verification_called, _, _}
    end

    parsed = request([{"content-type", "application/x-www-form-urlencoded"}])
    invalid_request(%{parsed | body_params: %{"access_token" => "secret"}}, opts)
    refute_receive {:verification_called, _, _}
  end

  test "duplicate, malformed, comma-joined and oversized Content-Type never select a convenient value",
       %{opts: opts} do
    for types <- [
          ["application/json", "application/x-www-form-urlencoded"],
          ["application/json", "application/json"],
          ["application/json, application/x-www-form-urlencoded"],
          ["application/x-www-form-urlencoded, application/json"],
          ["invalid"],
          ["application/"],
          ["application/ "],
          ["application/; charset=utf-8"],
          [~s(application/; profile="one,two")],
          ["application/; ;"],
          ["*/*"],
          [String.duplicate("a", 1_025)]
        ] do
      headers = [{"authorization", "Bearer a"} | Enum.map(types, &{"content-type", &1})]
      invalid_request(request(headers), opts)
      refute_receive {:verification_called, _, _}
    end
  end

  test "JSON and other bodies remain unread and tokens in them have no authentication fallback",
       %{opts: opts} do
    for type <- ["application/json", "application/octet-stream"], header? <- [true, false] do
      body = ~s({"access_token":"body-secret","role":"owner"})
      original = conn(:post, "/protected", body) |> put_req_header("content-type", type)

      original =
        if header?,
          do: put_req_header(original, "authorization", "Bearer header-token"),
          else: original

      result = BearerIdentity.call(original, opts)
      assert result.body_params == original.body_params
      assert result.params == original.params
      assert {:ok, ^body, _} = read_body(result)

      if header? do
        refute result.halted
        assert_receive {:verification_called, "header-token", @now}
      else
        assert_error(result, 401, "unauthenticated", "Bearer")
        refute_receive {:verification_called, _, _}
      end
    end
  end

  test "malformed Content-Type parameter tails reject without verification", %{opts: opts} do
    for type <- [
          "application/json; charset=utf-8, application/x-www-form-urlencoded",
          "application/json; invalid-parameter",
          ~s(application/json; profile="unterminated),
          "application/json; charset=",
          "application/json; charset =utf-8",
          "application/json; charset= utf-8",
          ~s(application/json; profile="ok"extra),
          "application/json\r\n; charset=utf-8"
        ] do
      invalid_request(request([{"authorization", "Bearer a"}, {"content-type", type}]), opts)
      refute_received {:verification_called, _, _}
    end
  end

  test "complete quoted parameters and empty parameter slots remain accepted", %{opts: opts} do
    for type <- [
          ~s(application/json; profile="one,two;three"),
          ~S(application/json; profile="one\"two\\three"),
          ~s(application/json; profile=""; charset=utf-8),
          "application/json; ; charset=utf-8;\t;",
          "application/json; profile=\"" <> <<128, 255>> <> "\""
        ] do
      result =
        request([{"authorization", "Bearer a"}, {"content-type", type}])
        |> BearerIdentity.call(opts)

      refute result.halted
      assert_received {:verification_called, "a", @now}
    end
  end

  test "Content-Type quoted values reject controls and require paired escapes", %{opts: opts} do
    for byte <- 0..255 do
      type = "application/json; profile=\"a" <> <<byte>> <> "b\""

      result =
        request([{"authorization", "Bearer a"}, {"content-type", type}])
        |> BearerIdentity.call(opts)

      if byte == 9 or byte in 32..33 or byte in 35..126 or byte >= 128 do
        refute result.halted, "allowed quoted byte #{byte}"
        assert_received {:verification_called, "a", @now}
      else
        assert result.status == 400, "forbidden quoted byte #{byte}"
        refute_received {:verification_called, _, _}
      end
    end
  end

  test "denials normalize every duplicate response metadata header", %{opts: opts} do
    for {headers, outcome, status, code, challenge} <- [
          {[], {:ok, identity()}, 401, "unauthenticated", "Bearer"},
          {[{"authorization", "Basic a"}], {:ok, identity()}, 400, "invalid_request",
           ~s(Bearer error="invalid_request")},
          {[{"authorization", "Bearer a"}], {:error, :unauthenticated}, 401, "unauthenticated",
           ~s(Bearer error="invalid_token")},
          {[{"authorization", "Bearer a"}], {:error, :identity_unavailable}, 503,
           "identity_unavailable", nil}
        ] do
      Process.put(:bearer_test_result, outcome)

      stale =
        for name <- [
              "x-request-id",
              "www-authenticate",
              "retry-after",
              "cache-control",
              "content-type"
            ],
            value <- [
              "old-response-first-12345",
              "old-response-second-12345",
              "old-response-third-12345"
            ],
            do: {name, value}

      original = %{request(headers) | resp_headers: [{"x-preserved", "yes"} | stale]}
      result = BearerIdentity.call(original, opts) |> assert_error(status, code, challenge)
      assert [id] = get_resp_header(result, "x-request-id")
      refute String.starts_with?(id, "old-response-")
      assert get_resp_header(result, "cache-control") == ["no-store"]
      assert get_resp_header(result, "content-type") == ["application/json; charset=utf-8"]
      assert get_resp_header(result, "x-preserved") == ["yes"]

      if headers == [{"authorization", "Bearer a"}],
        do: assert_received({:verification_called, "a", @now})
    end
  end

  test "successful identity admission also replaces duplicate request IDs and cache directives",
       %{opts: opts} do
    original = %{
      request()
      | resp_headers: [
          {"x-request-id", "old-response-first-12345"},
          {"x-request-id", "old-response-second-12345"},
          {"cache-control", "public"},
          {"cache-control", "max-age=600"}
        ]
    }

    result = BearerIdentity.call(original, opts)
    refute result.halted
    assert [_] = get_resp_header(result, "x-request-id")
    assert get_resp_header(result, "cache-control") == ["no-store"]
    assert_received {:verification_called, "exact.Token-1", @now}
  end

  test "cookies are ignored data and never become an identity mechanism", %{opts: opts} do
    cookie = {"cookie", "access_token=cookie-secret; session=cookie-session"}
    missing = request([cookie]) |> BearerIdentity.call(opts)
    assert_error(missing, 401, "unauthenticated", "Bearer")
    refute_receive {:verification_called, _, _}

    present =
      request([cookie, {"authorization", "Bearer header-token"}]) |> BearerIdentity.call(opts)

    refute present.halted
    assert_receive {:verification_called, "header-token", @now}
    assert present.req_cookies == %Plug.Conn.Unfetched{aspect: :cookies}
  end

  test "request IDs reuse a bounded safe upstream response ID and replace unsafe values", %{
    opts: opts
  } do
    id = "http-transport-request-12345"
    upstream = request([]) |> put_resp_header("x-request-id", id)

    result =
      upstream |> BearerIdentity.call(opts) |> assert_error(401, "unauthenticated", "Bearer")

    assert Jason.decode!(result.resp_body)["request_id"] == id

    for unsafe <- ["tiny", String.duplicate("a", 201), String.duplicate("a", 20) <> "\nsecret"] do
      original = %{request([]) | resp_headers: [{"x-request-id", unsafe}]}

      result =
        original |> BearerIdentity.call(opts) |> assert_error(401, "unauthenticated", "Bearer")

      refute Jason.decode!(result.resp_body)["request_id"] == unsafe
    end
  end

  test "existing Plug.RequestId output joins the JSON envelope", %{opts: opts} do
    original = Plug.RequestId.call(request([]), Plug.RequestId.init([]))

    result =
      original |> BearerIdentity.call(opts) |> assert_error(401, "unauthenticated", "Bearer")

    assert get_resp_header(result, "x-request-id") == get_resp_header(original, "x-request-id")
  end

  test "trusted dependency injection is closed and validated at init" do
    for options <- [
          %{},
          [unknown: true],
          [verifier: ProbeVerifier, verifier: ProbeVerifier],
          [verifier: "ProbeVerifier"],
          [verifier: String],
          [clock: fn -> @now end],
          [clock: {System, :does_not_exist, []}],
          [clock: {System, :system_time, :second}]
        ] do
      assert_raise ArgumentError, fn -> BearerIdentity.init(options) end
    end

    assert BearerIdentity.init([]) == %{
             verifier: ConfiguredVerifier,
             clock: {System, :system_time, [:second]}
           }
  end

  test "default clock forwards actual Unix seconds and invalid clock results fail closed" do
    before = System.system_time(:second)
    result = request() |> BearerIdentity.call(BearerIdentity.init(verifier: ProbeVerifier))
    after_time = System.system_time(:second)
    refute result.halted
    assert_receive {:verification_called, "exact.Token-1", time}
    assert time >= before and time <= after_time

    for function <- [:bad_clock, :raising_clock] do
      result = request() |> BearerIdentity.call(options(clock: {__MODULE__, function, []}))
      assert_error(result, 503, "identity_unavailable", nil)
      refute_receive {:verification_called, _, _}
    end
  end

  test "default ConfiguredVerifier with no started owner is unavailable, never a raw-token fallback" do
    assert Process.whereis(MixerHosted.Identity.KeyOwner) == nil

    assert ConfiguredVerifier.authenticate("synthetic.token", System.system_time(:second)) ==
             {:error, :identity_unavailable}

    result =
      request()
      |> assign(:verified_identity, identity())
      |> BearerIdentity.call(BearerIdentity.init([]))

    assert_error(result, 503, "identity_unavailable", nil)
  end

  defp sign(private, claims) do
    header = %{"alg" => "RS256", "typ" => "at+jwt", "kid" => "http-transport-owned-test-key"}
    JOSE.JWS.sign(private, Jason.encode!(claims), header) |> JOSE.JWS.compact() |> elem(1)
  end

  test "real RS256 and TrustSnapshot verification joins HTTP without granting token-claimed authority",
       c do
    Process.put(:bearer_test_snapshot, c.snapshot)
    token = sign(c.private, c.claims)
    opts = options(verifier: SnapshotVerifier)
    result = request([{"authorization", "Bearer " <> token}]) |> BearerIdentity.call(opts)

    assert %VerifiedIdentity{subject: "synthetic-http-subject", scopes: ["mixer.artifact.read"]} =
             result.assigns.verified_identity

    assert Map.keys(result.assigns) == [:verified_identity]
    refute result.halted
    assert_receive {:snapshot_verification_called, ^token, @now}
  end

  test "real signature, expiry, audience and snapshot freshness failures preserve generic HTTP denials",
       c do
    Process.put(:bearer_test_snapshot, c.snapshot)
    opts = options(verifier: SnapshotVerifier)
    good = sign(c.private, c.claims)
    [head, payload, signature] = :binary.split(good, ".", [:global])
    <<first, tail::binary>> = Base.url_decode64!(signature, padding: false)
    bad_signature = Base.url_encode64(<<Bitwise.bxor(first, 1), tail::binary>>, padding: false)

    for token <- [
          Enum.join([head, payload, bad_signature], "."),
          sign(c.private, %{c.claims | "exp" => @now}),
          sign(c.private, %{c.claims | "aud" => "wrong-audience"})
        ] do
      result =
        request([{"authorization", "Bearer " <> token}])
        |> assign(:verified_identity, identity())
        |> BearerIdentity.call(opts)

      assert_error(result, 401, "unauthenticated", ~s(Bearer error="invalid_token"))
      refute result.resp_body =~ "synthetic-http"
      assert_receive {:snapshot_verification_called, ^token, @now}
    end

    Process.put(:bearer_test_snapshot, %{c.snapshot | fresh_until: @now})
    result = request([{"authorization", "Bearer " <> good}]) |> BearerIdentity.call(opts)
    assert_error(result, 503, "identity_unavailable", nil)
  end
end
