defmodule MixerHosted.RuntimeConfigTest do
  use ExUnit.Case, async: true
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

  test "queue bounds cannot be widened or interpreted as arbitrary atoms" do
    for value <- ["0", "9", "infinity", "1.0"] do
      bad =
        processor_env()
        |> Map.put("MIXER_QUEUE_BUILDS_CONCURRENCY", value)

      assert_raise ArgumentError, fn -> RuntimeConfig.load!(bad) end
    end
  end
end
