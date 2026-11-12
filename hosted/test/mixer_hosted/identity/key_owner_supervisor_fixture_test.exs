defmodule MixerHosted.Identity.KeyOwnerSupervisorFixtureTest do
  use ExUnit.Case, async: false

  alias MixerHosted.Identity.{
    Admission,
    ConfiguredVerifier,
    KeyOwner,
    KeyOwnerSupervisor,
    StartupFixture,
    TrustSnapshot
  }

  @profile %{
    profile_id: "constructor-fixture",
    profile_version: 1,
    issuer: "https://issuer.fixture.invalid/oauth",
    audience: "mixer-api",
    client_id: "reviewed-client",
    identity_class: :human,
    enabled: true
  }
  @entry %{
    profile: @profile,
    jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"},
    transport: :hosted_https
  }

  setup_all do
    {:ok, _} = Application.ensure_all_started(:jose)
    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "constructor-key", "alg" => "RS256", "use" => "sig"})

    {:ok,
     key: key,
     jwks: Jason.encode!(%{"keys" => [public]}),
     root: hd(StartupFixture.standard_roots())}
  end

  test "fixture constructor registers the actual default owner when name is omitted", context do
    exercise_constructor([], KeyOwner, context)
  end

  test "fixture constructor preserves an explicit owner and its worker name", context do
    name = __MODULE__.ExplicitOwner
    exercise_constructor([name: name], name, context)
  end

  defp exercise_constructor(name_options, name, context) do
    workers = Module.concat(name, FetchSupervisor)
    assert Process.whereis(name) == nil
    assert Process.whereis(workers) == nil
    assert :persistent_term.get({Admission, name}, :absent) == :absent

    options =
      [
        manifest: [@entry],
        generation: 1,
        binding: @profile.profile_id,
        ca_roots: [context.root],
        resolvers: [{{127, 0, 0, 1}, 9}],
        fixture: %{ip: {127, 0, 0, 1}, port: 1}
      ] ++ name_options

    component =
      start_supervised!(%{
        id: name,
        start: {KeyOwnerSupervisor, :start_fixture, [options]},
        shutdown: :infinity
      })

    owner = Process.whereis(name)
    worker = Process.whereis(workers)
    assert is_pid(owner)
    assert is_pid(worker)
    state = :sys.get_state(owner)
    table = state.table

    on_exit(fn ->
      refute Process.alive?(component)
      refute Process.alive?(owner)
      refute Process.alive?(worker)
      assert Process.whereis(name) == nil
      assert Process.whereis(workers) == nil
      assert :ets.info(table) == :undefined
      assert :persistent_term.get({Admission, name}, :absent) == :absent
    end)

    assert state.name == name
    assert state.workers == workers
    assert :ets.info(table, :owner) == owner
    assert {KeyOwner, owner, :worker, [KeyOwner]} in Supervisor.which_children(component)

    now = System.system_time(:second)
    {:ok, snapshot} = TrustSnapshot.new(@profile, context.jwks, now - 1, now + 299)

    # Seed only validated public trust in this test-owned process. No transport runs.
    record = %{
      snapshot: snapshot,
      generation: make_ref(),
      expires_mono: System.monotonic_time(:millisecond) + 299_000
    }

    :sys.replace_state(owner, fn current ->
      %{current | snapshots: %{@profile.profile_id => record}}
    end)

    claims = %{
      "iss" => @profile.issuer,
      "aud" => @profile.audience,
      "sub" => "constructor-subject",
      "client_id" => @profile.client_id,
      "iat" => now - 1,
      "exp" => now + 120,
      "jti" => "constructor-token"
    }

    token =
      JOSE.JWS.sign(context.key, Jason.encode!(claims), %{
        "alg" => "RS256",
        "typ" => "at+jwt",
        "kid" => "constructor-key"
      })
      |> JOSE.JWS.compact()
      |> elem(1)

    assert {:ok, _identity} =
             ConfiguredVerifier.authenticate(name, @profile.profile_id, token, now)

    current = :sys.get_state(owner)
    assert current.attempts == %{}
    assert current.flights == %{}
    assert current.admitted == %{}
    assert DynamicSupervisor.count_children(workers).active == 0
    assert :ok = stop_supervised(name)
    refute Process.alive?(component)
    refute Process.alive?(owner)
    refute Process.alive?(worker)
  end
end
