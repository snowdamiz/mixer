defmodule MixerHosted.RuntimeConfigTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Releases.ReleaseJobs.{ProcessorAdmission, ProcessorProfile}
  alias MixerHosted.RuntimeConfig

  defp env do
    %{
      "MIXER_HOSTED_ROLE" => "api",
      "MIXER_DATABASE_HOST" => "ep-fixture.us-east-2.aws.neon.tech",
      "MIXER_DATABASE_NAME" => "mixer_fixture",
      "MIXER_DATABASE_USER" => "mixer_fixture",
      "MIXER_DATABASE_PASSWORD" => "synthetic-database-secret",
      "MIXER_SECRET_KEY_BASE" => String.duplicate("synthetic-secret-", 8)
    }
  end

  test "API cannot process jobs and uses bounded verified TLS connections" do
    config = RuntimeConfig.load!(env())
    assert config.role == :api
    assert config.oban[:queues] == []
    assert config.oban[:peer] == false
    assert config.oban[:stager] == [interval: :infinity]
    assert config.oban[:notifier] == Oban.Notifiers.Postgres
    assert config.repo[:pool_size] == 8
    assert config.repo[:pool_count] == 1
    assert config.database_connection_bound == 9
    assert config.repo[:ssl][:verify] == :verify_peer
    assert config.repo[:ssl][:cacerts] != []

    assert config.repo[:ssl][:server_name_indication] ==
             ~c"ep-fixture.us-east-2.aws.neon.tech"

    assert is_function(config.repo[:ssl][:customize_hostname_check][:match_fun], 2)
    assert config.endpoint[:http][:ip] == {127, 0, 0, 1}
    assert config.endpoint[:http][:http_2_options] == [enabled: false]
    refute inspect(config) =~ "synthetic"

    assert Enum.member?(
             MixerHosted.Application.children({config, :disabled}),
             MixerHostedWeb.Endpoint
           )
  end

  test "processor has separate bounded queues and no HTTP endpoint" do
    config = RuntimeConfig.load!(processor_env())

    assert Keyword.keys(config.oban[:queues]) ==
             [:builds]

    assert Enum.all?(config.oban[:queues], fn {_, limit} -> limit == 1 end)
    assert config.endpoint == [server: false]
    assert config.oban[:plugins] == []
    assert config.oban[:peer] == Oban.Peers.Database
    assert config.oban[:stager] == [interval: 1_000]

    refute Enum.member?(
             MixerHosted.Application.children({config, :disabled}),
             MixerHostedWeb.Endpoint
           )
  end

  test "required configuration fails closed without leaking values" do
    for key <- Map.keys(env()) do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> key, fn ->
        RuntimeConfig.load!(Map.delete(env(), key))
      end
    end

    for {key, value} <- [
          {"MIXER_HOSTED_ROLE", "api,processor"},
          {"MIXER_DATABASE_HOST", "ep-fixture-pooler.us-east-2.aws.neon.tech"},
          {"MIXER_DATABASE_HOST", "user:secret@db.example"},
          {"MIXER_DATABASE_HOST", "db.example?sslmode=disable"},
          {"MIXER_DATABASE_HOST", "db.example\n"},
          {"MIXER_DATABASE_HOST", "db..example"},
          {"MIXER_DATABASE_POOL_SIZE", "21"},
          {"MIXER_DATABASE_POOL_SIZE", "0"},
          {"MIXER_DATABASE_POOL_SIZE", "8junk"},
          {"MIXER_HTTP_BIND", "db.example"},
          {"MIXER_HTTP_PORT", "65536"},
          {"MIXER_SECRET_KEY_BASE", "short-secret"}
        ] do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> key, fn ->
        RuntimeConfig.load!(Map.put(env(), key, value))
      end
    end
  end

  defp processor_env do
    env()
    |> Map.merge(%{
      "MIXER_HOSTED_ROLE" => "processor",
      "MIXER_PROCESSOR_PROFILE" => "builds_v1",
      "MIXER_DATABASE_USER" => "mixer_build_processor"
    })
  end

  test "native loopback dispatch requires explicit durable builds selection" do
    native = %{
      "MIXER_BUILD_DISPATCH" => "native_development_v1",
      "MIXER_BUILD_OPERATION_INTENT" => "durable_intent_v1",
      "MIXER_NATIVE_WORKER_PORT" => "12345",
      "MIXER_NATIVE_WORKER_ID" => "local-worker",
      "MIXER_NATIVE_WORKER_TOKEN" => String.duplicate("token", 8),
      "MIXER_NATIVE_RETAINED_ROOT" => "/owned/native-state"
    }

    assert RuntimeConfig.load!(processor_env()).native == nil
    configured = Map.merge(processor_env(), native)
    settings = RuntimeConfig.load!(configured)

    assert %{port: 12345, worker_id: "local-worker", retained_root: "/owned/native-state"} =
             settings.native

    refute inspect(settings) =~ native["MIXER_NATIVE_WORKER_TOKEN"]

    for key <- Map.keys(native) do
      assert_raise ArgumentError, fn -> RuntimeConfig.load!(Map.delete(configured, key)) end
    end

    for {key, invalid} <- [
          {"MIXER_BUILD_DISPATCH", "Elixir.ArbitraryAdapter"},
          {"MIXER_NATIVE_WORKER_PORT", "0"},
          {"MIXER_NATIVE_WORKER_ID", "spaces refused"},
          {"MIXER_NATIVE_WORKER_TOKEN", "short"},
          {"MIXER_NATIVE_RETAINED_ROOT", "/owned/../other"}
        ] do
      assert_raise ArgumentError, fn -> RuntimeConfig.load!(Map.put(configured, key, invalid)) end
    end

    assert_raise ArgumentError, fn ->
      RuntimeConfig.load!(Map.merge(env(), Map.delete(native, "MIXER_BUILD_OPERATION_INTENT")))
    end
  end

  test "API independently opts in to retained artifact reads and restricted cancellation" do
    assert %{native: nil, build_cancel: false} = RuntimeConfig.load!(env())

    api =
      Map.merge(env(), %{
        "MIXER_PROCESSOR_PROFILE" => "builds_v1",
        "MIXER_BUILD_CREATE_ENABLED" => "true",
        "MIXER_BUILD_CREATE_PASSWORD" => "synthetic",
        "MIXER_BUILD_CANCEL_ENABLED" => "true",
        "MIXER_NATIVE_RETAINED_ROOT" => "/owned/native-state"
      })

    assert %{native: %{retained_root: "/owned/native-state"}, build_cancel: true} =
             RuntimeConfig.load!(api)

    for {key, invalid} <- [
          {"MIXER_BUILD_CANCEL_ENABLED", "yes"},
          {"MIXER_BUILD_CREATE_ENABLED", "false"},
          {"MIXER_NATIVE_WORKER_TOKEN", String.duplicate("token", 8)},
          {"MIXER_HTTP_BIND", "0.0.0.0"}
        ] do
      assert_raise ArgumentError, fn -> RuntimeConfig.load!(Map.put(api, key, invalid)) end
    end
  end

  test "processor requires explicit profile and direct login and refuses other queues" do
    for bad <- [
          Map.delete(processor_env(), "MIXER_PROCESSOR_PROFILE"),
          Map.put(processor_env(), "MIXER_DATABASE_USER", "mixer_fixture"),
          Map.put(processor_env(), "MIXER_QUEUE_SIGNING_CONCURRENCY", "1"),
          Map.put(processor_env(), "MIXER_PROCESSOR_PROFILE", "unknown")
        ] do
      assert_raise ArgumentError, fn -> RuntimeConfig.load!(bad) end
    end

    cfg = RuntimeConfig.load!(processor_env())
    assert cfg.processor_profile == :builds_v1
    assert cfg.repo[:after_connect] == {MixerHosted.Builds.ProcessorAdmission, :after_connect, []}

    assert [MixerHosted.Repo, {MixerHosted.Builds.ProcessorAdmission, :builds_v1}, {Oban, _}] =
             MixerHosted.Application.children({cfg, :disabled})

    assert cfg.database_connection_bound == cfg.repo[:pool_size] + 1
  end

  test "release jobs are an explicit API opt-in without a producer Oban instance" do
    key = "MIXER_LOCAL_RELEASE_JOBS_ENABLED"
    disabled = RuntimeConfig.load!(env())
    assert disabled.local_release_jobs == false
    assert RuntimeConfig.load!(Map.put(env(), key, "false")) == disabled

    assert RuntimeConfig.load!(Map.put(env(), key, "true")) == %{
             disabled
             | local_release_jobs: true
           }

    for bad <- [Map.put(env(), key, "yes"), Map.put(processor_env(), key, "true")] do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> key, fn ->
        RuntimeConfig.load!(bad)
      end
    end
  end

  test "release processor has only the admitted prefixed queue and the database pool" do
    env =
      processor_env()
      |> Map.put("MIXER_PROCESSOR_PROFILE", "releases_v1")
      |> Map.put("MIXER_DATABASE_USER", "mixer_release_processor")
      |> Map.put("MIXER_QUEUE_RELEASES_CONCURRENCY", "3")
      |> Map.delete("MIXER_SECRET_KEY_BASE")

    config = RuntimeConfig.load!(env)
    oban = config.oban
    assert config.processor_profile == :releases_v1
    assert config.endpoint == [server: false]
    assert config.local_release_jobs == false
    assert config.database_connection_bound == config.repo[:pool_size]
    assert config.repo[:after_connect] == {ProcessorAdmission, :after_connect, []}
    assert oban == ProcessorProfile.oban(3)
    assert oban[:queues] == [releases: 3]
    assert oban[:prefix] == "mixer_release_jobs"
    assert oban[:insert_trigger] == false
    assert oban[:notifier] == Oban.Notifiers.Isolated
    assert oban[:peer] == Oban.Peers.Database
    assert oban[:stager] == [interval: 1_000]

    assert [MixerHosted.Repo, {ProcessorAdmission, :releases_v1}, {Oban, ^oban}] =
             MixerHosted.Application.children({config, :disabled})

    for {key, value} <- [
          {"MIXER_HOSTED_ROLE", "api"},
          {"MIXER_DATABASE_USER", "mixer_build_processor"},
          {"MIXER_QUEUE_BUILDS_CONCURRENCY", "1"},
          {"MIXER_QUEUE_RELEASES_CONCURRENCY", "9"},
          {"MIXER_BUILD_OPERATION_INTENT", "durable_intent_v1"},
          {"MIXER_IDENTITY_MODE", "configured"}
        ] do
      assert_raise ArgumentError, fn -> RuntimeConfig.load!(Map.put(env, key, value)) end
    end

    for forged <- [
          %{config | oban: Keyword.put(oban, :prefix, "public")},
          %{config | oban: Keyword.put(oban, :queues, releases: 3, builds: 1)},
          %{config | repo: Keyword.delete(config.repo, :after_connect)},
          %{config | local_release_jobs: true}
        ] do
      assert_raise MatchError, fn -> MixerHosted.Application.children({forged, :disabled}) end
    end
  end

  test "queue bounds cannot be widened or interpreted as arbitrary atoms" do
    for value <- ["0", "9", "infinity", "1.0"] do
      bad =
        processor_env()
        |> Map.put("MIXER_QUEUE_BUILDS_CONCURRENCY", value)

      assert_raise ArgumentError, fn -> RuntimeConfig.load!(bad) end
    end
  end

  test "durable intent binds both admission hooks to the validated builds processor startup" do
    selector = "MIXER_BUILD_OPERATION_INTENT"
    selection = "durable_intent_v1"
    admission = MixerHosted.Builds.ProcessorAdmission

    default = RuntimeConfig.load!(processor_env())
    assert default.build_operation_intent == :disabled

    selected = RuntimeConfig.load!(Map.put(processor_env(), selector, selection))
    assert selected.build_operation_intent == :durable_intent_v1
    assert selected.repo[:after_connect] == {admission, :after_connect, [:durable_intent_v1]}

    assert [MixerHosted.Repo, {^admission, :durable_intent_v1}, {Oban, _}] =
             MixerHosted.Application.children({selected, :disabled})

    assert_raise MatchError, fn ->
      MixerHosted.Application.children({%{selected | repo: default.repo}, :disabled})
    end

    assert {:error, :restart_required} =
             MixerHosted.Application.config_change([], [], [:build_operation_intent])
  end

  test "durable intent selector rejects malformed values and other roles" do
    selector = "MIXER_BUILD_OPERATION_INTENT"
    api = Map.put(env(), "MIXER_PROCESSOR_PROFILE", "builds_v1")

    billing =
      processor_env()
      |> Map.put("MIXER_PROCESSOR_PROFILE", "billing_v1")
      |> Map.put("MIXER_DATABASE_USER", "mixer_billing_processor")

    for bad <- [
          Map.put(api, selector, "durable_intent_v1"),
          Map.put(billing, selector, "durable_intent_v1")
          | Enum.map(["", "disabled", "false", "durable_intent_v1 ", nil], fn value ->
              Map.put(processor_env(), selector, value)
            end)
        ] do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> selector, fn ->
        RuntimeConfig.load!(bad)
      end
    end
  end
end
