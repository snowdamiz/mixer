defmodule MixerHosted.Releases.RuntimeProvisioningTest do
  use ExUnit.Case

  alias MixerHosted.Releases.{RuntimeProvisioning, Target, WriterRepo}
  alias MixerHosted.Releases.EnvironmentPromotion.Direction
  alias MixerHosted.Releases.EnvironmentPromotion.Direction.Enrollment
  alias MixerHosted.RuntimeConfig

  @config "MIXER_LOCAL_RELEASE_CONFIG"
  @registry "MIXER_LOCAL_RELEASE_TARGET_REGISTRY"
  @directions "MIXER_LOCAL_STAGE_PROMOTION_DIRECTIONS"
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

  test "release jobs require the existing provisioned target and delivery pool", ctx do
    key = "MIXER_LOCAL_RELEASE_JOBS_ENABLED"
    enabled = RuntimeConfig.load!(Map.put(ctx.env, key, "true"))

    assert RuntimeProvisioning.load!(ctx.env, enabled) ==
             RuntimeProvisioning.load!(ctx.env, ctx.hosted)

    assert_raise ArgumentError, "invalid or missing hosted setting: " <> @config, fn ->
      RuntimeProvisioning.load!(@base, enabled)
    end
  end

  test "registers separate host and roots for each additional exact target", ctx do
    document = android_document(ctx.document)
    env = Map.put(ctx.env, @registry, Jason.encode!([document]))
    {default, delivery} = RuntimeProvisioning.load!(env, ctx.hosted)
    assert {^default, _} = RuntimeProvisioning.load!(ctx.env, ctx.hosted)
    refute ctx.hosted.local_release_jobs

    enabled = RuntimeConfig.load!(Map.put(env, "MIXER_LOCAL_RELEASE_JOBS_ENABLED", "true"))
    assert enabled.local_release_jobs
    assert {default, delivery} == RuntimeProvisioning.load!(env, enabled)

    assert [{target, %{target: target, host: host, roots: roots}}] =
             Map.to_list(delivery.registry)

    assert target.platform == "android"
    assert host == document["host"]
    assert Enum.all?(roots, &(&1["scope"] == host["scope"]))
  end

  test "rejects duplicate selections and cross-scope roots", ctx do
    document = android_document(ctx.document)

    for entries <- [
          [],
          [ctx.document],
          [document, document],
          [%{document | "roots" => ctx.document["roots"]}]
        ] do
      assert_raise ArgumentError, ~r/MIXER_LOCAL_RELEASE_TARGET_REGISTRY/, fn ->
        RuntimeProvisioning.load!(Map.put(ctx.env, @registry, Jason.encode!(entries)), ctx.hosted)
      end
    end
  end

  defp android_document(document) do
    with_target_scope(document, "platform", "android")
  end

  defp with_target_scope(document, field, value) do
    document
    |> put_in(["host", "scope", field], value)
    |> update_in(
      ["roots"],
      &Enum.map(&1, fn root -> put_in(root, ["scope", field], value) end)
    )
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

  describe "local stage promotion directions" do
    setup ctx do
      source_ios = ctx.document

      source_android =
        source_ios
        |> android_document()
        |> put_in(["host", "runtime"], String.duplicate("a", 64))

      destination_ios =
        source_ios
        |> with_target_scope("environment", "staging")
        |> put_in(["host", "runtime"], String.duplicate("b", 64))
        |> Map.put("channel", "stable")

      destination_android =
        destination_ios
        |> android_document()
        |> put_in(["host", "runtime"], String.duplicate("c", 64))

      additional = [source_android, destination_ios, destination_android]

      env =
        Map.merge(ctx.env, %{
          @registry => Jason.encode!(additional),
          @writer_enabled => "true"
        })

      direction = %{
        "direction_id" => "development-to-staging",
        "source" => %{"ios" => wire(source_ios), "android" => wire(source_android)},
        "destination" => %{"ios" => wire(destination_ios), "android" => wire(destination_android)}
      }

      %{promotion_env: env, direction: direction, additional: additional}
    end

    test "normal runtime config resolves both routes to their provisioned host and roots", ctx do
      reverse = %{
        "direction_id" => "staging-to-development",
        "source" => ctx.direction["destination"],
        "destination" => ctx.direction["source"]
      }

      env = Map.put(ctx.promotion_env, @directions, Jason.encode!([ctx.direction, reverse]))
      config = read_runtime!(env)
      {default, delivery} = RuntimeProvisioning.load!(ctx.promotion_env, ctx.hosted)

      assert config[:local_release_target] == default
      assert config[:local_release_delivery] == delivery
      assert config[WriterRepo] == Keyword.put(ctx.hosted.repo, :pool_size, 1)

      [source_android, destination_ios, destination_android] =
        Enum.map(ctx.additional, fn document ->
          Enum.find_value(delivery.registry, fn {_target, entry} ->
            if entry.host == document["host"], do: struct!(Enrollment, entry)
          end)
        end)

      source = %{ios: struct!(Enrollment, default), android: source_android}
      destination = %{ios: destination_ios, android: destination_android}

      assert config[:local_stage_promotion_directions] == %{
               "development-to-staging" => %Direction{source: source, destination: destination},
               "staging-to-development" => %Direction{source: destination, destination: source}
             }

      assert read_runtime!(ctx.promotion_env)[:local_stage_promotion_directions] == %{}
      assert read_runtime!(@base)[:local_stage_promotion_directions] == %{}
    end

    test "normal runtime config refuses directions without an enabled local API writer", ctx do
      raw = Jason.encode!([ctx.direction])
      env = Map.put(ctx.promotion_env, @directions, raw)

      processor =
        Map.merge(@base, %{
          @directions => raw,
          "MIXER_HOSTED_ROLE" => "processor",
          "MIXER_PROCESSOR_PROFILE" => "builds_v1",
          "MIXER_DATABASE_USER" => "mixer_build_processor"
        })

      for invalid_env <- [
            Map.delete(env, @writer_enabled),
            Map.put(@base, @directions, raw),
            processor
          ] do
        assert_raise ArgumentError, "invalid or missing hosted setting: " <> @directions, fn ->
          read_runtime!(invalid_env)
        end
      end
    end

    test "refuses malformed, duplicate, and unbounded direction input", ctx do
      direction = ctx.direction
      encoded = Jason.encode!([direction])

      invalid = [
        "",
        encoded <> String.duplicate(" ", 65_537 - byte_size(encoded)),
        String.replace(
          encoded,
          ~s("direction_id":),
          ~s("direction_\\u0069d":"other","direction_id":)
        ),
        Jason.encode!(direction),
        Jason.encode!([]),
        Jason.encode!([direction, direction]),
        Jason.encode!(for n <- 1..33, do: %{direction | "direction_id" => "direction-#{n}"}),
        Jason.encode!([Map.delete(direction, "direction_id")]),
        Jason.encode!([%{direction | "direction_id" => "invalid id"}]),
        Jason.encode!([Map.put(direction, "writer_role", "override")]),
        Jason.encode!([put_in(direction, ["source", "host"], ctx.document["host"])]),
        Jason.encode!([put_in(direction, ["destination", "ios", "roots"], ctx.document["roots"])])
      ]

      for raw <- invalid do
        assert_invalid_directions(ctx, ctx.promotion_env, raw)
      end
    end

    test "requires four exact registered targets with both platforms in different stages", ctx do
      direction = ctx.direction

      invalid = [
        update_in(direction, ["destination"], &Map.delete(&1, "android")),
        put_in(direction, ["source", "ios"], direction["source"]["android"]),
        put_in(direction, ["destination", "ios", "channel"], "unregistered"),
        put_in(
          direction,
          ["destination", "ios", "runtimeFingerprint"],
          String.duplicate("9", 64)
        ),
        put_in(direction, ["destination", "android"], direction["source"]["android"]),
        %{direction | "destination" => direction["source"]}
      ]

      for wrong <- invalid do
        assert_invalid_directions(ctx, ctx.promotion_env, Jason.encode!([wrong]))
      end

      env = Map.put(ctx.promotion_env, @registry, Jason.encode!(Enum.take(ctx.additional, 2)))
      assert_invalid_directions(ctx, env, Jason.encode!([direction]))
    end

    test "refuses exact registered targets from different organizations, projects, or apps",
         ctx do
      [_, destination_ios, destination_android] = ctx.additional

      for field <- ~w(organization project app) do
        other_ios = with_target_scope(destination_ios, field, "other")
        other_android = with_target_scope(destination_android, field, "other")
        additional = ctx.additional ++ [other_ios, other_android]
        env = Map.put(ctx.promotion_env, @registry, Jason.encode!(additional))

        for ios <- [destination_ios, other_ios] do
          direction =
            put_in(ctx.direction, ["destination"], %{
              "ios" => wire(ios),
              "android" => wire(other_android)
            })

          assert_invalid_directions(ctx, env, Jason.encode!([direction]))
        end
      end
    end
  end

  defp assert_invalid_directions(ctx, env, raw) do
    release = RuntimeProvisioning.load!(env, ctx.hosted)
    writer = RuntimeProvisioning.writer_options!(env, ctx.hosted, release)

    assert_raise ArgumentError, "invalid or missing hosted setting: " <> @directions, fn ->
      RuntimeProvisioning.stage_promotion_directions!(
        Map.put(env, @directions, raw),
        release,
        writer
      )
    end
  end

  defp read_runtime!(env) do
    previous = Map.filter(System.get_env(), fn {key, _} -> String.starts_with?(key, "MIXER_") end)
    Enum.each(Map.keys(previous), &System.delete_env/1)
    System.put_env(env)

    try do
      Config.Reader.read!("config/runtime.exs", env: :prod) |> Keyword.fetch!(:mixer_hosted)
    after
      Enum.each(Map.keys(env), &System.delete_env/1)
      System.put_env(previous)
    end
  end

  defp wire(%{"host" => %{"scope" => scope, "runtime" => runtime}, "channel" => channel}) do
    %{
      "organizationId" => scope["organization"],
      "projectId" => scope["project"],
      "applicationId" => scope["app"],
      "environmentId" => scope["environment"],
      "platform" => scope["platform"],
      "runtimeFingerprint" => runtime,
      "channel" => channel
    }
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
