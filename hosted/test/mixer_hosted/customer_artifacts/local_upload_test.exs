defmodule MixerHosted.CustomerArtifacts.LocalUploadTest do
  use ExUnit.Case, async: false

  alias MixerHosted.{CustomerArtifacts, RuntimeConfig}
  alias MixerHosted.CustomerArtifacts.{LocalUpload, UploadRepo}
  alias MixerHosted.Releases.{DeliveryRepo, RuntimeProvisioning, WriterRepo}
  alias MixerHostedWeb.Endpoint

  @enabled "MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED"
  @password "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD"
  @login "mixer_artifact_uploader"
  @base %{
    "MIXER_HOSTED_ROLE" => "api",
    "MIXER_DATABASE_HOST" => "db.fixture.example",
    "MIXER_DATABASE_NAME" => "mixer_fixture",
    "MIXER_DATABASE_USER" => "api_fixture",
    "MIXER_DATABASE_PASSWORD" => "api-fixture",
    "MIXER_BUILD_CREATE_ENABLED" => "true",
    "MIXER_BUILD_CREATE_PASSWORD" => "create-fixture",
    "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8)
  }
  @upload %{@enabled => "true", @password => "uploader-fixture"}

  setup do
    vector =
      "../../../../services/protocol/testdata/signed-release-v3.json"
      |> Path.expand(__DIR__)
      |> File.read!()
      |> Jason.decode!()

    doc = %{
      host: vector["host"],
      roots: vector["roots"],
      channel: vector["signed_assignment"]["assignment"]["channel"]
    }

    env =
      Map.merge(@base, %{
        "MIXER_LOCAL_RELEASE_CONFIG" => Jason.encode!(doc),
        "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD" => "reader-fixture"
      })

    hosted = RuntimeConfig.load!(env)
    release = RuntimeProvisioning.load!(env, hosted)
    %{hosted: hosted, release: release}
  end

  test "default off preserves the ordinary and build-create settings", ctx do
    for env <- [%{}, %{@enabled => "false"}] do
      assert LocalUpload.configure!(env, ctx.hosted, ctx.release) == ctx.hosted
      assert LocalUpload.children(ctx.hosted, :disabled, ctx.hosted.endpoint) == []
    end
  end

  test "one additional connection inherits the existing database and verified TLS", ctx do
    {target, delivery} = ctx.release
    settings = LocalUpload.configure!(@upload, ctx.hosted, ctx.release)
    assert settings.database_connection_bound == ctx.hosted.database_connection_bound + 1
    assert settings.create_repo == ctx.hosted.create_repo
    assert settings.repo == ctx.hosted.repo
    assert settings.artifact_upload.release == target

    assert settings.artifact_upload.repo ==
             Keyword.merge(ctx.hosted.repo,
               username: @login,
               password: @upload[@password],
               pool_size: 1
             )

    assert settings.artifact_upload.repo[:ssl][:verify] == :verify_peer

    set_env(:local_release_target, target)
    set_env(:local_release_delivery, delivery)
    endpoint = [adapter: Bandit.PhoenixAdapter] ++ ctx.hosted.endpoint
    set_env(Endpoint, endpoint)
    assert [{UploadRepo, options}] = LocalUpload.children(settings, :disabled, endpoint)
    assert options == settings.artifact_upload.repo
  end

  test "rejects partial settings, extra inputs, and conflicting users or passwords", ctx do
    for env <- [
          %{@enabled => "true"},
          %{@password => "stray"},
          put_in(@upload[@enabled], "false"),
          put_in(@upload[@enabled], "1"),
          put_in(@upload[@password], ""),
          put_in(@upload[@password], <<0>>),
          put_in(@upload[@password], ctx.hosted.repo[:password]),
          put_in(@upload[@password], ctx.hosted.create_repo[:password]),
          put_in(@upload[@password], "reader-fixture"),
          Map.put(@upload, "MIXER_LOCAL_ARTIFACT_UPLOAD_USER", "another-login"),
          Map.put(@upload, "MIXER_LOCAL_ARTIFACT_UPLOAD_HTTP_PORT", "1234")
        ] do
      assert_raise ArgumentError, fn -> LocalUpload.configure!(env, ctx.hosted, ctx.release) end
    end

    assert_raise ArgumentError, fn -> LocalUpload.configure!(@upload, ctx.hosted, :disabled) end

    for hosted <- [
          %{ctx.hosted | role: :processor},
          RuntimeConfig.load!(Map.put(@base, "MIXER_HTTP_BIND", "0.0.0.0")),
          RuntimeConfig.load!(Map.put(@base, "MIXER_DATABASE_USER", @login))
        ] do
      assert_raise ArgumentError, fn -> LocalUpload.configure!(@upload, hosted, ctx.release) end
    end
  end

  test "refuses extra effective listeners, pool overrides, and mismatched release settings",
       ctx do
    {target, delivery} = ctx.release
    settings = LocalUpload.configure!(@upload, ctx.hosted, ctx.release)
    set_env(:local_release_target, target)
    set_env(:local_release_delivery, delivery)
    endpoint = [adapter: Bandit.PhoenixAdapter] ++ ctx.hosted.endpoint

    for effective <- [
          endpoint ++ [https: [ip: {127, 0, 0, 1}]],
          endpoint ++ [http: [ip: {0, 0, 0, 0}]],
          Keyword.put(endpoint, :adapter, :unknown_adapter)
        ] do
      assert_raise ArgumentError, fn -> LocalUpload.children(settings, :disabled, effective) end
    end

    for {key, value} <- [
          {CustomerArtifacts, %{repo: UploadRepo}},
          {UploadRepo, [pool_count: 2]},
          {DeliveryRepo, [url: "postgres://unexpected"]},
          {WriterRepo, [username: @login]},
          {WriterRepo,
           Keyword.merge(ctx.hosted.repo, pool_size: 1, url: "postgres://unexpected")},
          {:local_release_delivery, put_in(delivery.repo[:pool_count], 2)},
          {:local_release_target, %{target | target: %{target.target | channel: "other"}}}
        ] do
      original = Application.fetch_env(:mixer_hosted, key)
      Application.put_env(:mixer_hosted, key, value)

      try do
        assert_raise ArgumentError, fn -> LocalUpload.children(settings, :disabled, endpoint) end
      after
        restore_env(key, original)
      end
    end
  end

  defp set_env(key, value) do
    original = Application.fetch_env(:mixer_hosted, key)
    Application.put_env(:mixer_hosted, key, value)
    on_exit(fn -> restore_env(key, original) end)
  end

  defp restore_env(key, {:ok, value}), do: Application.put_env(:mixer_hosted, key, value)
  defp restore_env(key, :error), do: Application.delete_env(:mixer_hosted, key)
end
