defmodule MixerHosted.Releases.RuntimeProvisioningTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Releases.{RuntimeProvisioning, Target}
  alias MixerHosted.RuntimeConfig

  @config "MIXER_LOCAL_RELEASE_CONFIG"
  @password "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD"
  @writer_enabled "MIXER_LOCAL_RELEASE_WRITER_ENABLED"
  @fixture Path.expand(
             "../../../../services/protocol/testdata/signed-release-v3.json",
             __DIR__
           )
  @base %{
    "MIXER_HOSTED_ROLE" => "api",
    "MIXER_DATABASE_HOST" => "db.fixture.example",
    "MIXER_DATABASE_NAME" => "mixer_fixture",
    "MIXER_DATABASE_USER" => "mixer_fixture",
    "MIXER_DATABASE_PASSWORD" => "ordinary-fixture-password",
    "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8)
  }

  setup do
    fixture = @fixture |> File.read!() |> Jason.decode!()
    channel = fixture["signed_assignment"]["assignment"]["channel"]
    document = %{"host" => fixture["host"], "channel" => channel, "roots" => fixture["roots"]}
    env = Map.merge(@base, %{@config => Jason.encode!(document), @password => "reader-password"})
    %{document: document, env: env, hosted: RuntimeConfig.load!(@base)}
  end

  test "an absent pair is disabled and either half alone aborts startup", %{
    env: env,
    hosted: hosted
  } do
    assert RuntimeProvisioning.load!(@base, hosted) == :disabled

    for key <- [@config, @password] do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> key, fn ->
        RuntimeProvisioning.load!(Map.delete(env, key), hosted)
      end
    end
  end

  test "projects one exact target and preserves DB TLS and transport", ctx do
    {target, delivery} = RuntimeProvisioning.load!(ctx.env, ctx.hosted)

    assert %{target: %Target{} = selection, host: host, roots: roots} = target
    assert host == ctx.document["host"]
    assert Target.signed_scope(selection) == host["scope"]
    assert selection.runtime_sha256 == host["runtime"]
    assert selection.channel == ctx.document["channel"]

    assert roots ==
             Enum.map(
               ctx.document["roots"],
               &Map.update!(&1, "public_key", fn key ->
                 Base.decode64!(key)
               end)
             )

    assert Map.delete(delivery, :repo) == target

    assert delivery.repo ==
             Keyword.merge(ctx.hosted.repo,
               username: "mixer_release_delivery",
               password: "reader-password",
               pool_size: 1
             )

    assert delivery.repo[:ssl][:verify] == :verify_peer
    assert delivery.repo[:port] == 5432
  end

  test "rejects invalid, ambiguous, or unbounded target metadata and trust roots", ctx do
    root = hd(ctx.document["roots"])

    invalid = [
      "",
      "{" <>
        ~s("chann\\u0065l":"other",) <>
        binary_part(ctx.env[@config], 1, byte_size(ctx.env[@config]) - 1),
      String.duplicate(" ", 65_537),
      Jason.encode!(Map.put(ctx.document, "database_url", "unexpected")),
      Jason.encode!(put_in(ctx.document, ["host", "runtime"], "invalid-digest")),
      Jason.encode!(Map.put(ctx.document, "channel", "*")),
      Jason.encode!(Map.put(ctx.document, "roots", [])),
      Jason.encode!(Map.put(ctx.document, "roots", [root, root])),
      Jason.encode!(Map.put(ctx.document, "roots", [Map.put(root, "private_key", "unexpected")])),
      Jason.encode!(Map.put(ctx.document, "roots", [Map.put(root, "public_key", "bogus")])),
      Jason.encode!(Map.put(ctx.document, "roots", [put_in(root, ["scope", "app"], "other")]))
    ]

    for raw <- invalid do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> @config, fn ->
        RuntimeProvisioning.load!(Map.put(ctx.env, @config, raw), ctx.hosted)
      end
    end
  end

  test "retains structurally valid revoked roots for request-time policy", ctx do
    document =
      Map.update!(
        ctx.document,
        "roots",
        &Enum.map(&1, fn root -> %{root | "revoked" => true} end)
      )

    {target, _} =
      RuntimeProvisioning.load!(Map.put(ctx.env, @config, Jason.encode!(document)), ctx.hosted)

    assert Enum.all?(target.roots, & &1["revoked"])
  end

  test "keeps legacy delivery reader-only unless the writer is explicitly enabled", ctx do
    assert RuntimeProvisioning.writer_options!(@base, ctx.hosted, :disabled) == nil
    release = RuntimeProvisioning.load!(ctx.env, ctx.hosted)
    assert RuntimeProvisioning.writer_options!(ctx.env, ctx.hosted, release) == nil

    env = Map.put(ctx.env, @writer_enabled, "false")
    assert RuntimeProvisioning.writer_options!(env, ctx.hosted, release) == nil
  end

  test "projects one verified connection with the ordinary API login", ctx do
    env = Map.put(ctx.env, @writer_enabled, "true")
    {_, delivery} = release = RuntimeProvisioning.load!(env, ctx.hosted)
    writer = RuntimeProvisioning.writer_options!(env, ctx.hosted, release)

    assert writer == Keyword.put(ctx.hosted.repo, :pool_size, 1)
    assert writer[:pool_count] == 1
    assert writer[:ssl][:verify] == :verify_peer
    assert writer[:username] != delivery.repo[:username]
    assert writer[:show_sensitive_data_on_connection_error] == false
  end

  test "requires the target and reader for opt-in and refuses other writer settings", ctx do
    release = RuntimeProvisioning.load!(ctx.env, ctx.hosted)
    enabled = Map.put(ctx.env, @writer_enabled, "true")

    for {env, hosted, provisioning} <- [
          {enabled, ctx.hosted, :disabled},
          {enabled, %{ctx.hosted | role: :processor}, release},
          {Map.put(ctx.env, @writer_enabled, ""), ctx.hosted, release},
          {Map.put(ctx.env, @writer_enabled, "1"), ctx.hosted, release}
        ] do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> @writer_enabled, fn ->
        RuntimeProvisioning.writer_options!(env, hosted, provisioning)
      end
    end
  end

  test "refuses processors, public binds, and shared reader credentials", ctx do
    invalid = [
      {"MIXER_HOSTED_ROLE", %{ctx.hosted | role: :processor}, ctx.env},
      {"MIXER_HTTP_BIND", RuntimeConfig.load!(Map.put(@base, "MIXER_HTTP_BIND", "0.0.0.0")),
       ctx.env},
      {"MIXER_DATABASE_USER",
       RuntimeConfig.load!(Map.put(@base, "MIXER_DATABASE_USER", "mixer_release_delivery")),
       ctx.env},
      {@password, ctx.hosted, Map.put(ctx.env, @password, @base["MIXER_DATABASE_PASSWORD"])},
      {@password, ctx.hosted, Map.put(ctx.env, @password, "")}
    ]

    for {setting, hosted, env} <- invalid do
      assert_raise ArgumentError, "invalid or missing hosted setting: " <> setting, fn ->
        RuntimeProvisioning.load!(env, hosted)
      end
    end
  end
end
