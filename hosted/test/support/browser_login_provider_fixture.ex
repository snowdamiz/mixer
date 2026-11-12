defmodule R686.AuthorizationHTTP do
  import Plug.Conn
  def init(opts), do: opts

  def call(conn, %{provider: provider, config: config}) do
    if conn.method == "GET" and conn.request_path == "/authorize" do
      code = GenServer.call(provider, {:register, conn.query_string})
      state = URI.decode_query(conn.query_string)["state"]
      query = URI.encode_query([{"state", state}, {"iss", config.issuer}, {"code", code}])

      conn
      |> put_resp_header("location", config.redirect_uri <> "?" <> query)
      |> send_resp(302, "")
    else
      send_resp(conn, 404, "")
    end
  end
end

defmodule R686.Provider do
  use GenServer
  alias MixerHosted.BrowserAuth.Protocol
  def start_link(opts), do: GenServer.start_link(__MODULE__, opts)
  def init(opts), do: {:ok, Map.merge(opts, %{codes: %{}, mode: :ok, count: 0})}

  def handle_call({:register, query}, _, s) do
    values = URI.decode_query(query)
    code = Protocol.random_token()
    {:reply, code, put_in(s.codes[code], values)}
  end

  def handle_call({:mode, mode}, _, s), do: {:reply, :ok, %{s | mode: mode}}
  def handle_call(:count, _, s), do: {:reply, s.count, s}

  def handle_call({:exchange, r}, _, s) do
    {v, codes} = Map.pop(s.codes, r.code)
    s = %{s | codes: codes, count: s.count + 1}

    valid =
      v !== nil and r.issuer === s.config.issuer and r.client_id === v["client_id"] and
        r.redirect_uri === v["redirect_uri"] and r.token_endpoint === s.config.token_endpoint and
        r.grant_type === "authorization_code" and r.client_auth_method === :client_secret_basic and
        r.client_credential_ref === s.config.client_credential_ref and
        Protocol.pkce_challenge(r.code_verifier) === {:ok, v["code_challenge"]}

    cond do
      not valid or s.mode === :pkce ->
        {:reply, {:error, :invalid_grant}, s}

      s.mode === :late ->
        Process.sleep(1100)
        {:reply, {:error, :late}, s}

      true ->
        now = System.system_time(:second)

        claims = %{
          "iss" => s.config.issuer,
          "aud" => s.config.api_audience,
          "sub" => "subject-1",
          "client_id" => s.config.client_id,
          "iat" => now - 1,
          "exp" => now + if(s.mode === :short, do: 2, else: 120),
          "jti" => Protocol.random_token(),
          "scope" =>
            if(s.mode == :no_build_scope,
              do: "mixer.workspace.read",
              else: String.replace(v["scope"], "openid ", "")
            )
        }

        access = sign(s.key, claims, "at+jwt")
        <<half::binary-size(16), _::binary>> = :crypto.hash(:sha256, access)

        id = %{
          "iss" => s.config.issuer,
          "aud" => s.config.client_id,
          "sub" => "subject-1",
          "iat" => now - 1,
          "exp" =>
            now +
              case s.mode do
                :short -> 2
                :session_short -> 45
                _ -> 120
              end,
          "nonce" => v["nonce"],
          "at_hash" => Base.url_encode64(half, padding: false)
        }

        id =
          case s.mode do
            :nonce -> Map.put(id, "nonce", Protocol.random_token())
            :aud -> Map.put(id, "aud", "wrong-client")
            :issuer -> Map.put(id, "iss", "https://wrong.example.invalid")
            :link -> Map.put(id, "at_hash", Protocol.random_token())
            :azp -> id |> Map.put("aud", [s.config.client_id, "other"]) |> Map.put("azp", "other")
            :expired -> Map.put(id, "exp", now - 2)
            _ -> id
          end

        token = sign(if(s.mode === :signature, do: s.wrong_key, else: s.key), id, "JWT")
        if is_tuple(s.mode), do: send(elem(s.mode, 1), {:provider_exchange, self()})

        if is_tuple(s.mode) do
          receive do
            :continue -> :ok
          after
            1500 -> :ok
          end
        end

        {:reply,
         {:ok,
          Jason.encode!(%{
            "token_type" => "Bearer",
            "access_token" => access,
            "id_token" => token
          })}, s}
    end
  end

  defp sign(k, c, t),
    do:
      JOSE.JWS.sign(k, Jason.encode!(c), %{"alg" => "RS256", "typ" => t, "kid" => "key1"})
      |> JOSE.JWS.compact()
      |> elem(1)
end

defmodule R966.LoginFixture do
  alias MixerHosted.BrowserAuth.StorageFixture, as: Original
  defdelegate port(), to: Original
  defdelegate q!(repo, sql, params \\ []), to: Original
  defdelegate call(conn, name, args), to: Original
  def install!, do: Original.install!()

  def connection!(role \\ "browser_lifecycle", database \\ "browser_login_storage") do
    {:ok, conn} =
      Postgrex.start_link(
        hostname: "127.0.0.1",
        port: port(),
        username: role,
        database: database,
        ssl: false,
        backoff_type: :stop
      )

    Process.unlink(conn)
    Postgrex.query!(conn, "SET statement_timeout='5s'", [])
    Postgrex.query!(conn, "SET lock_timeout='500ms'", [])
    Postgrex.query!(conn, "SET idle_in_transaction_session_timeout='5s'", [])
    conn
  end

  def provision! do
    conn = connection!("browser_admin")

    try do
      for sql <-
            MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
              "browser_writer",
              "browser_lifecycle"
            ),
          do: Postgrex.query!(conn, sql, [])
    after
      GenServer.stop(conn)
    end
  end
end

