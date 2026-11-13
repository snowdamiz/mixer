# Isolated production composition controls; LifecycleRepo/RuntimeOwner/Endpoint below are fake leaves.
# These controls prove construction and supervision boundaries, never database admission.
[jason_lib] = System.argv()
root = Path.expand("../..", __DIR__)
Mix.start()
Mix.env(:prod)
{:ok, _} = Application.ensure_all_started(:public_key)
{:ok, _} = Application.ensure_all_started(:ssl)

unless Code.ensure_loaded?(Jason) do
  {_, []} =
    Code.with_diagnostics(fn ->
      {:ok, _, _} =
        Kernel.ParallelCompiler.compile(Path.wildcard(Path.join(jason_lib, "**/*.ex")),
          return_diagnostics: true
        )
    end)
end

true = Code.ensure_loaded?(HPAX)
true = Code.ensure_loaded?(Mint.HTTP)
true = Code.ensure_loaded?(JOSE.JWK)
true = Code.ensure_loaded?(JOSE.JWS)

# Isolated supervision-boundary leaves. These are never copied into afterimages.
# The existing ordinary fixture needs a provisioned PostgreSQL schema/role harness.
defmodule MixerHosted.BrowserAuth.LifecycleRepo do
  use GenServer
  def start_link(options), do: GenServer.start_link(__MODULE__, options, name: __MODULE__)
  def init(_options), do: {:ok, :storage_not_qualified}
end

defmodule MixerHosted.BrowserAuth.RuntimeOwner do
  use GenServer
  def start_link(runtime), do: GenServer.start_link(__MODULE__, runtime, name: __MODULE__)

  def init(runtime) do
    names = [
      MixerHosted.BrowserAuth.LifecycleRepo,
      MixerHosted.BrowserAuth.ProviderTrustOwner,
      MixerHosted.BrowserAuth.ProviderTrustOwner.FetchSupervisor,
      MixerHosted.BrowserAuth.ProviderOwner
    ]

    if Enum.all?(names, &is_pid(Process.whereis(&1))) and
         runtime.admission_profile == :build_catalog_v3,
       do: {:ok, :runtime_not_qualified},
       else: {:stop, :dependency_order}
  end

  def status, do: %{phase: :test_leaf_only}
end

defmodule MixerHostedWeb.Endpoint do
  def config_change(_, _), do: :ok
end

inputs = [
  "hosted/lib/mixer_hosted/application.ex",
  "hosted/lib/mixer_hosted/browser_auth/config.ex",
  "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
  "hosted/lib/mixer_hosted/browser_auth/custody.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_https.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_https_wire.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_owner.ex",
  "hosted/lib/mixer_hosted/browser_auth/provider_trust_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex",
  "hosted/lib/mixer_hosted/browser_auth/vault.ex",
  "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
  "hosted/lib/mixer_hosted/identity/admission.ex",
  "hosted/lib/mixer_hosted/identity/bounded_json.ex",
  "hosted/lib/mixer_hosted/identity/bounded_tcp.ex",
  "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
  "hosted/lib/mixer_hosted/identity/dns_resolver.ex",
  "hosted/lib/mixer_hosted/identity/encoding.ex",
  "hosted/lib/mixer_hosted/identity/fetch_flight.ex",
  "hosted/lib/mixer_hosted/identity/global_address.ex",
  "hosted/lib/mixer_hosted/identity/http_freshness.ex",
  "hosted/lib/mixer_hosted/identity/http_wire_guard.ex",
  "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
  "hosted/lib/mixer_hosted/identity/key_owner.ex",
  "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
  "hosted/lib/mixer_hosted/identity/manifest.ex",
  "hosted/lib/mixer_hosted/identity/startup_config.ex",
  "hosted/lib/mixer_hosted/identity/trust_snapshot.ex",
  "hosted/lib/mixer_hosted/identity/verified_identity.ex",
  "hosted/lib/mixer_hosted/identity/verifier.ex",
  "hosted/lib/mixer_hosted/runtime_config.ex",
  "hosted/lib/mixer_hosted/browser_auth/installation.ex",
  "hosted/lib/mixer_hosted/browser_auth/supervisor.ex"
]

{_, []} =
  Code.with_diagnostics(fn ->
    {:ok, _, _} =
      Kernel.ParallelCompiler.compile(Enum.map(inputs, &Path.join(root, &1)),
        return_diagnostics: true
      )
  end)

for {module, function, arity} <- [
      {MixerHosted.BrowserAuth.Installation, :fixture!, 4},
      {MixerHosted.BrowserAuth.ProviderOwner, :start_fixture, 3},
      {MixerHosted.BrowserAuth.ProviderOwner, :start_production_fixture, 5},
      {MixerHosted.BrowserAuth.ProviderOwner, :start_trust_fixture, 2},
      {MixerHosted.BrowserAuth.ProviderHTTPS, :post_fixture, 8},
      {MixerHosted.Identity.KeyOwnerSupervisor, :start_fixture, 1}
    ],
    do: false = function_exported?(module, function, arity)

defmodule R1758.Fixture do
  alias MixerHosted.BrowserAuth.Config
  alias MixerHosted.RuntimeConfig, as: HostedConfig

  def fixtures do
    profile = %{
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => "https://identity.example.invalid/tenant",
      "audience" => "mixer-api",
      "client_id" => "mixer-console",
      "identity_class" => "human",
      "enabled" => true
    }

    identity = %{
      "version" => 1,
      "generation" => 1,
      "binding" => "human-main",
      "resolvers" => ["1.1.1.1"],
      "profiles" => [
        %{
          "profile" => profile,
          "jwks_endpoint" => %{
            "host" => "identity.example.invalid",
            "port" => 443,
            "path" => "/api/keys"
          },
          "transport" => "hosted_https"
        }
      ]
    }

    hosted =
      HostedConfig.load!(%{
        "MIXER_HOSTED_ROLE" => "api",
        "MIXER_DATABASE_HOST" => "ep-fixture.us-east-2.aws.neon.tech",
        "MIXER_DATABASE_NAME" => "mixer_fixture",
        "MIXER_DATABASE_USER" => "mixer_ordinary_fixture",
        "MIXER_DATABASE_PASSWORD" => "synthetic-ordinary-password",
        "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-secret-", 8),
        "MIXER_IDENTITY_MODE" => "configured",
        "MIXER_IDENTITY_CONFIG" => Jason.encode!(identity)
      })

    object = %{
      "version" => 1,
      "public_origin" => "https://console.example.invalid",
      "profile_id" => "human-main",
      "profile_version" => 7,
      "issuer" => profile["issuer"],
      "client_id" => "mixer-console",
      "api_audience" => "mixer-api",
      "authorization_endpoint" => "https://identity.example.invalid/authorize",
      "token_endpoint" => "https://identity.example.invalid/token",
      "id_token_jwks_endpoint" => "https://identity.example.invalid/oidc/keys",
      "redirect_uri" => "https://console.example.invalid/auth/callback",
      "client_auth_method" => "client_secret_basic",
      "client_credential_ref" => "secret://mixer/client-v1",
      "session_vault_ref" => "vault://mixer/session-v1",
      "scope" => "openid mixer.workspace.read mixer.build.read",
      "response_mode" => "query",
      "response_iss_required" => true
    }

    env = %{
      "MIXER_BROWSER_AUTH_MODE" => "configured",
      "MIXER_BROWSER_AUTH_CONFIG" => Jason.encode!(object)
    }

    {:ok, config} = Config.load(env, :api, hosted.identity_startup)

    material = %{
      "version" => 1,
      "client" => %{
        "reference" => object["client_credential_ref"],
        "value" => "synthetic-client-credential:+雪"
      },
      "session_vault" => %{
        "reference" => object["session_vault_ref"],
        "key_id" => "synthetic-v1",
        "key_base64" => Base.encode64(:binary.copy(<<71>>, 32))
      },
      "lifecycle" => %{
        "username" => "mixer_lifecycle_fixture",
        "password" => "synthetic-lifecycle-password",
        "writer_role" => "mixer_writer_fixture",
        "relation_owner" => "mixer_owner_fixture"
      }
    }

    {hosted, env, config, material}
  end
end

ExUnit.start(autorun: false, seed: 0, trace: true, timeout: 15000)

defmodule R1758.ConfiguredStartupTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{Installation, ProviderOwner, RuntimeOwner}
  alias MixerHosted.BrowserAuth.Supervisor, as: BrowserSupervisor
  alias MixerHosted.Application, as: HostedApplication
  @material "MIXER_BROWSER_AUTH_SECRET_MATERIAL"
  @error "browser installation unavailable: configuration"

  defp fixture do
    {hosted, browser, config, material} = R1758.Fixture.fixtures()
    env = Map.put(browser, @material, Jason.encode!(material))
    {hosted, env, config, material}
  end

  defp valid(value, message), do: assert(value === true, message)

  defp refused(env, hosted),
    do: assert_raise(ArgumentError, @error, fn -> Installation.load!(env, hosted) end)

  test "configured_browser_startup_from_reference_bound_material" do
    {hosted, env, config, material} = fixture()
    installation = Installation.load!(env, hosted)
    valid(Installation.valid?(installation, hosted), "installation validation")
    valid(installation.runtime.browser_config === config, "exact browser config")

    valid(
      installation.secrets.client_credential.value === material["client"]["value"],
      "exact material"
    )

    children = HostedApplication.children({hosted, installation})
    assert Enum.at(children, 0) == MixerHosted.Repo
    assert Enum.at(children, 1) == {Oban, hosted.oban}

    assert Enum.at(children, 2) ==
             {MixerHosted.Identity.KeyOwnerSupervisor, hosted.identity_startup.owner_options}

    assert Enum.at(children, 3) == {BrowserSupervisor, installation}
    assert List.last(children) == MixerHostedWeb.Endpoint
    pid = start_supervised!({BrowserSupervisor, installation})

    expected = [
      MixerHosted.BrowserAuth.LifecycleRepo,
      MixerHosted.BrowserAuth.ProviderTrustOwner,
      ProviderOwner,
      RuntimeOwner
    ]

    assert Enum.map(Supervisor.which_children(pid), &elem(&1, 0)) |> Enum.reverse() == expected
    assert :sys.get_state(Process.whereis(ProviderOwner)).transport.destination == :production
    assert RuntimeOwner.status() == %{phase: :test_leaf_only}
    worker = Process.whereis(MixerHosted.BrowserAuth.ProviderTrustOwner.FetchSupervisor)
    assert is_pid(worker)
    assert DynamicSupervisor.which_children(worker) == []

    for term <- [
          installation,
          :sys.get_status(pid),
          :sys.get_status(Process.whereis(ProviderOwner))
        ] do
      printed = inspect(term, limit: :infinity, printable_limit: :infinity)

      for marker <- [
            material["client"]["value"],
            material["lifecycle"]["password"],
            material["session_vault"]["key_base64"],
            installation.secrets.custody.key.bytes
          ] do
        valid(not String.contains?(printed, marker), "status redaction")
      end
    end
  end

  test "provider failure stops the whole browser lifetime without restart" do
    {hosted, env, _, _} = fixture()
    installation = Installation.load!(env, hosted)
    pid = start_supervised!({BrowserSupervisor, installation})
    monitor = Process.monitor(pid)
    children = Supervisor.which_children(pid)
    refs = for {_, child, _, _} <- children, do: {Process.monitor(child), child}
    Process.exit(Process.whereis(ProviderOwner), :kill)
    assert_receive {:DOWN, ^monitor, :process, ^pid, :shutdown}, 3000
    for {ref, child} <- refs, do: assert_receive({:DOWN, ^ref, :process, ^child, _}, 3000)
    assert Process.whereis(ProviderOwner) == nil
    assert Process.whereis(RuntimeOwner) == nil
    assert Process.whereis(MixerHosted.BrowserAuth.ProviderTrustOwner.FetchSupervisor) == nil
    assert BrowserSupervisor.child_spec(installation).restart == :temporary
  end

  test "same hosted config is required including ordinary endpoint and role projections" do
    {hosted, env, _, _} = fixture()
    installation = Installation.load!(env, hosted)

    for altered <- [
          %{hosted | role: :processor},
          %{hosted | endpoint: [server: false]},
          %{hosted | repo: Keyword.put(hosted.repo, :username, "another_ordinary")}
        ] do
      valid(not Installation.valid?(installation, altered), "same hosted value")

      assert_raise ArgumentError, @error, fn ->
        HostedApplication.children({altered, installation})
      end
    end

    valid(
      not Installation.valid?(
        %{installation | runtime: %{installation.runtime | admission_profile: :browser_auth_v2}},
        hosted
      ),
      "catalog contract"
    )

    valid(not Installation.valid?(%{installation | trust: nil}, hosted), "fixed trust required")

    assert BrowserSupervisor.init(%{installation | trust: nil}) ==
             {:stop, :browser_installation_unavailable}
  end

  test "disabled and processor create no browser or provider capabilities" do
    {hosted, env, _, _} = fixture()
    assert Installation.load!(%{}, hosted) == :disabled
    assert Installation.load!(%{@material => "invalid ignored material"}, hosted) == :disabled

    refute Enum.any?(
             HostedApplication.children({hosted, :disabled}),
             &match?({BrowserSupervisor, _}, &1)
           )

    refused(env, %{hosted | role: :processor})
    refused(Map.put(env, "MIXER_BROWSER_AUTH_MODE", "disabled"), hosted)
    disabled_identity = %MixerHosted.Identity.StartupConfig{mode: :disabled, owner_options: []}
    processor = %{hosted | role: :processor, identity_startup: disabled_identity}

    assert HostedApplication.children({processor, :disabled}) == [
             MixerHosted.Repo,
             {Oban, hosted.oban}
           ]
  end

  test "missing stale aliased and malformed secret materials fail before children" do
    {hosted, env, _, material} = fixture()
    refused(Map.delete(env, @material), hosted)

    for raw <- ["", "{}", "null", "[]", <<255>>, String.duplicate(" ", 16385)],
        do: refused(Map.put(env, @material, raw), hosted)

    for {section, bad} <- [
          {"client", "secret://mixer/client-v2"},
          {"session_vault", "vault://mixer/./session-v1"}
        ] do
      changed = put_in(material, [section, "reference"], bad)
      refused(Map.put(env, @material, Jason.encode!(changed)), hosted)
    end

    for secret <- ["", "bad\r\nheader", String.duplicate("x", 4097)] do
      changed = put_in(material, ["client", "value"], secret)
      refused(Map.put(env, @material, Jason.encode!(changed)), hosted)
    end

    assert Process.whereis(ProviderOwner) == nil
  end

  test "all four roles database direct host TLS and fixed trust remain enforced" do
    {hosted, env, _, material} = fixture()
    changed = put_in(material, ["lifecycle", "username"], hosted.repo[:username])
    refused(Map.put(env, @material, Jason.encode!(changed)), hosted)

    for repo <- [
          Keyword.put(hosted.repo, :hostname, "127.0.0.1"),
          Keyword.put(hosted.repo, :ssl, false),
          Keyword.put(hosted.repo, :port, 15432),
          Keyword.put(hosted.repo, :pool_size, 21),
          Keyword.put(hosted.repo, :hostname, "ep-a-pooler.example.invalid")
        ] do
      refused(env, %{hosted | repo: repo})
    end

    for option <- [
          fixture: %{ip: {127, 0, 0, 1}, port: 4443},
          transport: :fake,
          resolvers: [{{127, 0, 0, 1}, 9953}]
        ] do
      identity = %{
        hosted.identity_startup
        | owner_options: Keyword.merge(hosted.identity_startup.owner_options, [option])
      }

      refused(env, %{hosted | identity_startup: identity})
    end
  end

  test "ordinary startup environment drift refuses before root and ETS ownership is not forged" do
    {hosted, env, _, _} = fixture()
    installation = Installation.load!(env, hosted)
    prior = Application.get_all_env(:mixer_hosted)

    try do
      Application.put_env(:mixer_hosted, :startup, {hosted, installation})

      assert_raise ArgumentError, "hosted startup requires restart", fn ->
        HostedApplication.start(:normal, [])
      end

      assert HostedApplication.startup() == :error

      assert HostedApplication.config_change([role: :processor], [], []) ==
               {:error, :restart_required}

      assert Process.whereis(MixerHosted.Supervisor) == nil
    after
      for {key, _} <- Application.get_all_env(:mixer_hosted),
          do: Application.delete_env(:mixer_hosted, key)

      for {key, value} <- prior, do: Application.put_env(:mixer_hosted, key, value)
    end
  end
end

Code.require_file(
  Path.join(root, "hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs")
)

result = ExUnit.run()

names = [
  MixerHosted.Supervisor,
  MixerHosted.BrowserAuth.LifecycleRepo,
  MixerHosted.BrowserAuth.ProviderTrustOwner,
  MixerHosted.BrowserAuth.ProviderTrustOwner.FetchSupervisor,
  MixerHosted.BrowserAuth.ProviderOwner,
  MixerHosted.BrowserAuth.RuntimeOwner
]

true = Enum.all?(names, &(Process.whereis(&1) == nil))

false =
  Enum.any?(Application.started_applications(), fn {app, _, _} ->
    app in [:mixer_hosted, :postgrex, :oban, :bandit]
  end)

IO.puts(
  "CONFIGURED_COMPOSITION_RESULT=" <>
    Jason.encode!(%{
      result: result,
      mix_env: Mix.env(),
      fake_leaves: ["LifecycleRepo", "RuntimeOwner", "Endpoint.config_change"],
      database_admission_proved: false,
      all_owned_names_absent: true,
      application_started: false
    })
)

if result.total != 15 or result.failures != 0 or result.skipped != 0, do: System.halt(1)
