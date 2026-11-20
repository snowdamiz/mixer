defmodule MixerHosted.CustomerBuilds.LocalStarter do
  @moduledoc "One opt-in, operator-pinned worker registration for an exported starter."
  alias MixerHosted.CustomerBuilds.{CreateInput, CreateRepo, CreateSchema, Inputs}
  alias MixerHosted.CustomerBuilds.LocalStarterSchema, as: Schema
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.BrowserAuth.ActiveCreate

  @action "build.create"
  @scope [:organization_id, :project_id, :application_id]
  @max_files 2048
  @max_file 4 * 1024 * 1024
  @max_tree 32 * 1024 * 1024
  @max_tool 64 * 1024 * 1024
  @stat_options [:raw]
  @spec_keys ~w(organization_id project_id application_id platform source toolchain_lock_sha256 build_definition_sha256)
  @tool_environment ~w(PATH DEVELOPER_DIR LANG LC_ALL)
  @starter_package_closure "v38-local-v1"
  @starter_sdk_prefix "Generated/MixerSDK/"
  @starter_sdk_sha256 "ee03d620f05de3ecf3bb1242ab14da76082ca9b7d26ddcfbf72f8c82c967d50b"
  @starter_app_sha256 "9a3675d963109cb0d3e67b4230c1d2013a16a135263178d1c09a3fa7c6b38672"
  @android_driver "Generated/MixerAndroid/android-build.py"
  @excluded ~w(.build .git .swiftpm node_modules .gradle .mixer target .DS_Store)
  @private_suffix ~w(.pem .key .p12 .pfx .mobileprovision .keystore .jks)

  @doc false
  def runtime_config!(env) do
    keys = ~w(MIXER_LOCAL_STARTER_ORGANIZATION MIXER_LOCAL_STARTER_PROJECT
      MIXER_LOCAL_STARTER_APPLICATION MIXER_LOCAL_STARTER_REGISTRATION MIXER_LOCAL_STARTER_SHA256
      MIXER_LOCAL_STARTER_WORKER_SHA256)

    case Enum.map(keys, &Map.get(env, &1)) do
      [nil, nil, nil, nil, nil, nil] ->
        nil

      [org, project, app, path, pin, worker_pin] when is_binary(path) ->
        scope = %{organization_id: org, project_id: project, application_id: app}

        if match?({:ok, _}, Inputs.new(scope, nil)) and Path.type(path) == :absolute and
             Path.expand(path) == path and digest?(pin) and digest?(worker_pin),
           do: %{scope: scope, path: path, sha256: pin, worker_sha256: worker_pin},
           else: raise(ArgumentError, "invalid local starter configuration")

      _ ->
        raise ArgumentError, "incomplete local starter configuration"
    end
  end

  def parse(
        %{
          "organization_id" => org,
          "project_id" => project,
          "application_id" => app,
          "starter_id" => id
        } = body
      )
      when map_size(body) == 4 do
    scope = %{organization_id: org, project_id: project, application_id: app}

    with {:ok, _} <- Inputs.new(scope, nil),
         true <- CreateInput.id?(id) do
      {:ok, scope, id}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def parse(_), do: {:error, :invalid_request}

  def run(identity, scope, selection) do
    with {:ok, _} <- Inputs.new(scope, nil) do
      MixerHosted.Authorization.with_authorized_transaction(
        identity,
        @action,
        scope,
        fn context ->
          Context.effect!(context, CreateRepo, @action, context.target, fn snapshot ->
            CreateSchema.admit!(
              CreateRepo,
              MixerHosted.RuntimeConfig.installed_processor_profile()
            )

            ActiveCreate.require_browser_current!(context)

            if Enum.any?(snapshot.memberships, &organization_owner?/1) do
              available = available(scope, selection)
              ActiveCreate.require_browser_current!(context)
              apply_selection(scope, selection, available)
            else
              {:error, :permission_denied}
            end
          end)
        end,
        CreateRepo
      )
    end
  end

  defp available(scope, :list), do: load(scope)

  defp available(scope, {:select, id}) do
    case Application.get_env(:mixer_hosted, __MODULE__) do
      %{scope: ^scope, sha256: pin} when id == "starter-" <> pin -> load(scope)
      _ -> {:error, :not_found}
    end
  end

  defp organization_owner?(%{
         role: "owner",
         project_binding: :all_projects,
         scope: %{project_id: nil}
       }),
       do: true

  defp organization_owner?(_), do: false

  defp apply_selection(scope, :list, {:ok, starter}) do
    case selection_status(scope, starter, false) do
      "available" -> {:ok, Map.put(public_scope(scope), :starter, %{id: starter.id})}
      "missing" -> {:ok, Map.put(public_scope(scope), :starter, nil)}
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp apply_selection(scope, :list, _), do: {:ok, Map.put(public_scope(scope), :starter, nil)}

  defp apply_selection(scope, {:select, id}, {:ok, %{id: id} = starter}) do
    case selection_status(scope, starter, true) do
      "selected" ->
        %{
          "platform" => platform,
          "source" => %{"sha256" => source},
          "toolchain_lock_sha256" => lock,
          "build_definition_sha256" => definition
        } = starter.spec

        {:ok, %{inputs: [input]}} =
          Inputs.project(scope, [[platform, id, source, lock, definition]])

        {:ok, Map.merge(public_scope(scope), input)}

      "denied" ->
        {:error, :permission_denied}

      "missing" ->
        {:error, :not_found}

      "conflict" ->
        {:error, :conflict}

      _ ->
        {:error, :authorization_unavailable}
    end
  end

  defp apply_selection(_, {:select, _}, _), do: {:error, :not_found}

  defp selection_status(_scope, %{spec: %{"platform" => "android"}} = starter, select?) do
    Schema.admit!(CreateRepo, :android)

    [status] =
      Session.one!(
        CreateRepo,
        "SELECT public.mixer_local_android_starter_v1($1,$2,$3,$4,$5)",
        [starter.id, starter.pin, starter.spec, select?, starter.worker_pin],
        :authorization_unavailable
      )

    status
  end

  defp selection_status(scope, starter, select?) do
    Schema.admit!(CreateRepo)

    [status] =
      Session.one!(
        CreateRepo,
        "SELECT public.mixer_local_starter_v1($1,$2,$3,$4)",
        [starter.id, starter.pin, starter.spec, select? and starter.local_closure?],
        :authorization_unavailable
      )

    if status == "available" and not starter.local_closure? do
      existing_selection(scope, starter, select?)
    else
      status
    end
  end

  # A legacy selection is a read of the already-persisted receipt. It never
  # enters the SQL writer, even if the input disappears concurrently.
  defp existing_selection(scope, %{id: id, spec: spec}, select?) do
    source = spec["source"]

    rows =
      Session.query!(
        CreateRepo,
        """
        SELECT platform,input_id,source_kind,source_reference,source_sha256,
          toolchain_lock_sha256,build_definition_sha256,max_attempts,timeout_ms,retry_backoff_ms
        FROM public.mixer_customer_build_inputs
        WHERE organization_id=$1 AND project_id=$2 AND application_id=$3
        LIMIT 2
        """,
        [scope.organization_id, scope.project_id, scope.application_id]
      ).rows

    expected = [
      "ios",
      id,
      source["kind"],
      source["reference"],
      source["sha256"],
      spec["toolchain_lock_sha256"],
      spec["build_definition_sha256"],
      1,
      1_800_000,
      0
    ]

    case rows do
      [^expected] -> if(select?, do: "selected", else: "available")
      [] -> "missing"
      _ -> if(select?, do: "conflict", else: "missing")
    end
  end

  defp public_scope(scope) do
    %{
      organizationId: scope.organization_id,
      projectId: scope.project_id,
      applicationId: scope.application_id
    }
  end

  @doc false
  def load(scope) do
    with %{scope: ^scope, path: path, sha256: pin, worker_sha256: worker_pin} <-
           Application.get_env(:mixer_hosted, __MODULE__),
         {:ok, raw} <- read(path, 512 * 1024),
         ^pin <- sha(raw),
         {:ok,
          %{
            "tenant" => tenant,
            "registration" => grant,
            "policy" => policy,
            "worker" => %{
              "configuration_sha256" => ^worker_pin,
              "id" => worker_id,
              "port" => port
            }
          }} <- Jason.decode(raw),
         true <- CreateInput.id?(worker_id) and is_integer(port) and port in 1..65_535,
         %{"spec" => spec, "files" => files, "root" => root, "recipe" => recipe} <- grant,
         ^tenant <- scope.organization_id,
         true <-
           Map.take(spec, Enum.map(@scope, &Atom.to_string/1)) ==
             Map.new(scope, fn {k, v} -> {Atom.to_string(k), v} end),
         %{
           "platform" => platform,
           "source" => %{"kind" => kind, "reference" => ref, "sha256" => tree} = source,
           "toolchain_lock_sha256" => lock,
           "build_definition_sha256" => definition
         } <- spec,
         true <- Enum.sort(Map.keys(spec)) == Enum.sort(@spec_keys) and map_size(source) == 3,
         true <- kind in ["upload", "revision"] and CreateInput.id?(ref),
         id = "starter-" <> pin,
         {:ok, %{inputs: [_]}} <- Inputs.project(scope, [[platform, id, tree, lock, definition]]),
         %{"recipe_sha256" => ^definition} <- policy,
         true <-
           is_map(files) and map_size(files) in 1..@max_files and files["mixer.lock"] == lock,
         {:ok, recipe_bytes} <- read(recipe, 512 * 1024),
         ^definition <- sha(recipe_bytes),
         {:ok, ^files, _} <- inventory(root),
         ^tree <- tree_digest(files),
         {:ok, recipe} <- Jason.decode(recipe_bytes),
         true <- recipe_matches?(recipe, policy, platform, root, files),
         {:ok, local_closure?} <- package_closure(platform, recipe, policy, root, files) do
      {:ok,
       %{id: id, pin: pin, spec: spec, worker_pin: worker_pin, local_closure?: local_closure?}}
    else
      _ -> {:error, :not_found}
    end
  rescue
    _ -> {:error, :not_found}
  end

  defp recipe_matches?(recipe, policy, platform, root, files) do
    with %{
           "argv" => [cli, "build", "--platform", ^platform, "--directory", ^root],
           "cwd" => ^root,
           "environment" => %{"PATH" => "/usr/bin:/bin:/usr/sbin:/sbin"} = env,
           "inputs" => inputs,
           "tools" => tools,
           "timeout_seconds" => timeout
         }
         when is_integer(timeout) and timeout in 1..1800 <- recipe,
         %{"cli" => ^cli, "inputs" => ^inputs, "tools" => ^tools, "environment" => ^env} <- policy,
         true <- Map.keys(env) -- @tool_environment == [],
         true <- Enum.all?(env, fn {_name, value} -> is_binary(value) end),
         true <- is_map(inputs) and Enum.all?(inputs, fn {name, hash} -> files[name] == hash end),
         true <- is_map(tools) and recipe_profile?(platform, recipe, cli, tools) do
      Enum.all?(tools, fn {path, hash} ->
        # The installed Android Python can live below the admin-writable Cellar.
        # Its file still has to be canonical, pinned, and protected from group writes.
        ancestor_mask =
          if platform == "android" and path == recipe["android_python"], do: 0o002, else: 0o022

        case read(path, @max_tool, 0o022, ancestor_mask) do
          {:ok, contents} -> sha(contents) == hash
          _ -> false
        end
      end)
    else
      _ -> false
    end
  end

  defp recipe_profile?("ios", recipe, cli, tools) do
    match?(
      %{
        "profile" => "unsigned-ios-simulator-v1",
        "package_policy" => "exact-owned-local-manifests-no-external-packages"
      },
      recipe
    ) and Enum.sort(Map.keys(tools)) == Enum.sort([cli, "/usr/bin/xcodebuild"])
  end

  defp recipe_profile?(
         "android",
         %{
           "profile" => "unsigned-android-local-v1",
           "package_policy" => "exact-locked-android-file-mirrors-v1",
           "android_host_swift" => "/usr/bin/swift",
           "android_python" => python
         },
         cli,
         tools
       ) do
    Enum.sort(Map.keys(tools)) == Enum.sort([cli, "/usr/bin/swift", python])
  end

  defp recipe_profile?(_, _, _, _), do: false

  defp package_closure("android", recipe, policy, root, files) do
    # Installation files and mirrors are checked by the pinned worker verifier
    # during provisioning and at dispatch. Verify the export and its lock here.
    python = recipe["android_python"]
    python_pin = %{"path" => python, "sha256" => recipe["tools"][python]}

    with false <- Map.has_key?(recipe, "starter_package_closure"),
         false <- Map.has_key?(policy, "starter_package_closure"),
         true <- recipe["inputs"] == files and Map.has_key?(files, @android_driver),
         {:ok, lock} <- read(Path.join(root, "mixer.lock"), @max_file),
         true <- sha(lock) == files["mixer.lock"],
         {:ok, %{"android" => %{"toolchain" => %{"tools" => %{"python" => ^python_pin}}}}} <-
           Jason.decode(lock) do
      {:ok, true}
    end
  end

  defp package_closure("ios", recipe, policy, root, files) do
    case {Map.fetch(recipe, "starter_package_closure"),
          Map.fetch(policy, "starter_package_closure")} do
      {:error, :error} ->
        {:ok, false}

      {{:ok, @starter_package_closure}, {:ok, @starter_package_closure}} ->
        {sdk, app} =
          files
          |> Map.delete("mixer.lock")
          |> Enum.split_with(fn {name, _} -> String.starts_with?(name, @starter_sdk_prefix) end)

        sdk =
          Enum.map(sdk, fn {name, hash} ->
            {String.replace_prefix(name, @starter_sdk_prefix, ""), hash}
          end)

        with true <- recipe["inputs"] == files,
             @starter_sdk_sha256 <- tree_digest(sdk),
             @starter_app_sha256 <- tree_digest(app),
             {:ok, lock} <- read(Path.join(root, "mixer.lock"), @max_file),
             true <- sha(lock) == files["mixer.lock"],
             {:ok, %{"sdkDigest" => @starter_sdk_sha256}} <- Jason.decode(lock) do
          {:ok, true}
        end

      _ ->
        :error
    end
  end

  defp inventory(root) do
    with true <- canonical?(root),
         {:ok, %{type: :directory} = info} <- File.lstat(root, @stat_options),
         {:ok, {files, bytes, _}} <- walk(root, "", info, {%{}, 0, 0}),
         true <- canonical?(root) do
      {:ok, files, bytes}
    end
  end

  # Recheck each directory after all its descendants have been read. This
  # keeps the ancestor checks in the traversal instead of repeating them
  # for every directory in the export.
  defp walk(directory, relative, %{type: :directory, mode: mode} = info, {files, bytes, entries})
       when Bitwise.band(mode, 0o222) == 0 do
    with {:ok, names} <- File.ls(directory),
         count = entries + length(names),
         true <- count <= @max_files,
         {:ok, result} <-
           Enum.reduce_while(names, {:ok, {files, bytes, count}}, fn name, {:ok, state} ->
             case inventory_entry(directory, relative, name, state) do
               {:ok, _} = scanned -> {:cont, scanned}
               _ -> {:halt, :error}
             end
           end),
         true <- same_file?(directory, info) do
      {:ok, result}
    end
  end

  defp walk(path, relative, %{type: :regular} = info, {files, bytes, entries}) do
    with {:ok, body} <- read_snapshot(path, info, min(@max_file, @max_tree - bytes), 0o222) do
      {:ok, {Map.put(files, relative, sha(body)), bytes + byte_size(body), entries}}
    end
  end

  defp walk(_, _, _, _), do: :error

  defp inventory_entry(directory, relative, name, state) do
    path = Path.join(directory, name)

    with true <- name not in @excluded and not String.starts_with?(String.downcase(name), ".env"),
         false <- String.downcase(Path.extname(name)) in @private_suffix,
         true <- String.valid?(name) and not String.contains?(name, ["\n", "\r"]),
         {:ok, info} <- File.lstat(path, @stat_options) do
      walk(path, Path.join(relative, name), info, state)
    end
  end

  defp read(path, limit, write_mask \\ 0o222, ancestor_mask \\ 0o022) do
    with true <- canonical?(path, ancestor_mask),
         {:ok, info} <- File.lstat(path, @stat_options) do
      read_snapshot(path, info, limit, write_mask)
    end
  end

  defp read_snapshot(
         path,
         %{type: :regular, size: size, links: links, mode: mode} = before,
         limit,
         write_mask
       )
       when size <= limit and Bitwise.band(mode, write_mask) == 0 and
              (links == 1 or write_mask == 0o022) do
    with {:ok, file} <- File.open(path, [:read, :binary, :raw]) do
      bytes =
        try do
          if size == 0, do: {:ok, ""}, else: :file.read(file, size + 1)
        after
          File.close(file)
        end

      with {:ok, data} when byte_size(data) == size <- bytes,
           true <- same_file?(path, before) do
        {:ok, data}
      else
        _ -> :error
      end
    end
  end

  defp read_snapshot(_, _, _, _), do: :error

  defp same_file?(path, before) do
    case File.lstat(path, @stat_options) do
      {:ok, after_read} -> %{after_read | atime: before.atime} == before
      _ -> false
    end
  end

  defp canonical?(path, write_mask \\ 0o022)

  defp canonical?(path, write_mask) when is_binary(path) do
    Path.type(path) == :absolute and Path.expand(path) == path and
      path
      |> Path.split()
      |> Enum.scan(&Path.join(&2, &1))
      |> Enum.all?(fn part ->
        case File.lstat(part, @stat_options) do
          {:ok, %{type: type, mode: mode}} when type in [:regular, :directory] ->
            Bitwise.band(mode, write_mask) == 0

          _ ->
            false
        end
      end)
  end

  defp canonical?(_, _), do: false

  defp tree_digest(files) do
    files |> Enum.sort() |> Enum.map(fn {path, value} -> [path, 0, value, ?\n] end) |> sha()
  end

  defp digest?(value), do: is_binary(value) and Regex.match?(~r/\A[0-9a-f]{64}\z/, value)

  defp sha(bytes), do: :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)
end
