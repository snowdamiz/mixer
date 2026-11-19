defmodule MixerHosted.CustomerBuilds.LocalStarter do
  @moduledoc "One opt-in, operator-pinned worker registration for an exported iOS starter."
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
  @spec_keys ~w(organization_id project_id application_id platform source toolchain_lock_sha256 build_definition_sha256)
  @tool_environment ~w(PATH DEVELOPER_DIR LANG LC_ALL)
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
    Schema.admit!(CreateRepo)

    [provisioned] =
      Session.one!(
        CreateRepo,
        "SELECT public.mixer_local_starter_v1($1,$2,$3,false)",
        [starter.id, starter.pin, starter.spec],
        :authorization_unavailable
      )

    case provisioned do
      "available" -> {:ok, Map.put(public_scope(scope), :starter, %{id: starter.id})}
      "missing" -> {:ok, Map.put(public_scope(scope), :starter, nil)}
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp apply_selection(scope, :list, _), do: {:ok, Map.put(public_scope(scope), :starter, nil)}

  defp apply_selection(scope, {:select, id}, {:ok, %{id: id} = starter}) do
    Schema.admit!(CreateRepo)

    [result] =
      Session.one!(
        CreateRepo,
        "SELECT public.mixer_local_starter_v1($1,$2,$3,true)",
        [id, starter.pin, starter.spec],
        :authorization_unavailable
      )

    case result do
      "selected" ->
        %{
          "source" => %{"sha256" => source},
          "toolchain_lock_sha256" => lock,
          "build_definition_sha256" => definition
        } = starter.spec

        {:ok, %{inputs: [input]}} = Inputs.project(scope, [["ios", id, source, lock, definition]])
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
           "platform" => "ios",
           "source" => %{"kind" => kind, "reference" => ref, "sha256" => tree} = source,
           "toolchain_lock_sha256" => lock,
           "build_definition_sha256" => definition
         } <- spec,
         true <- Enum.sort(Map.keys(spec)) == Enum.sort(@spec_keys) and map_size(source) == 3,
         true <- kind in ["upload", "revision"] and CreateInput.id?(ref),
         id = "starter-" <> pin,
         {:ok, %{inputs: [_]}} <- Inputs.project(scope, [["ios", id, tree, lock, definition]]),
         %{"recipe_sha256" => ^definition} <- policy,
         true <-
           is_map(files) and map_size(files) in 1..@max_files and files["mixer.lock"] == lock,
         {:ok, recipe_bytes} <- read(recipe, 512 * 1024),
         ^definition <- sha(recipe_bytes),
         {:ok, ^files, _} <- inventory(root),
         ^tree <- tree_digest(files),
         true <- recipe_matches?(recipe_bytes, policy, root, files) do
      {:ok, %{id: id, pin: pin, spec: spec}}
    else
      _ -> {:error, :not_found}
    end
  rescue
    _ -> {:error, :not_found}
  end

  defp recipe_matches?(bytes, policy, root, files) do
    with {:ok,
          %{
            "argv" => [cli, "build", "--platform", "ios", "--directory", ^root],
            "cwd" => ^root,
            "environment" => %{"PATH" => "/usr/bin:/bin:/usr/sbin:/sbin"} = env,
            "profile" => "unsigned-ios-simulator-v1",
            "package_policy" => "exact-owned-local-manifests-no-external-packages",
            "inputs" => inputs,
            "tools" => tools,
            "timeout_seconds" => timeout
          }}
         when is_integer(timeout) and timeout in 1..1800 <- Jason.decode(bytes),
         %{"cli" => ^cli, "inputs" => ^inputs, "tools" => ^tools, "environment" => ^env} <- policy,
         true <- Map.keys(env) -- @tool_environment == [],
         true <- Enum.all?(env, fn {_name, value} -> is_binary(value) end),
         true <- is_map(inputs) and Enum.all?(inputs, fn {name, hash} -> files[name] == hash end),
         true <-
           is_map(tools) and Enum.sort(Map.keys(tools)) == Enum.sort([cli, "/usr/bin/xcodebuild"]) do
      Enum.all?(tools, fn {path, hash} ->
        case read(path, @max_tool, 0o022) do
          {:ok, contents} -> sha(contents) == hash
          _ -> false
        end
      end)
    else
      _ -> false
    end
  end

  defp inventory(root) do
    with true <- canonical?(root),
         {:ok, %{type: :directory, mode: mode}} when Bitwise.band(mode, 0o222) == 0 <-
           File.lstat(root) do
      walk(root, [""], %{}, 0, 0)
    end
  end

  defp walk(_, [], files, bytes, _), do: {:ok, files, bytes}

  defp walk(root, [relative | pending], files, bytes, entries) do
    with {:ok, names} <- File.ls(Path.join(root, relative)),
         true <- entries + length(names) <= @max_files do
      Enum.reduce_while(names, {:ok, pending, files, bytes}, fn name, {:ok, dirs, acc, total} ->
        child = Path.join(relative, name)
        path = Path.join(root, child)

        result =
          with true <-
                 name not in @excluded and not String.starts_with?(String.downcase(name), ".env"),
               false <- String.downcase(Path.extname(name)) in @private_suffix,
               true <- String.valid?(name) and not String.contains?(name, ["\n", "\r"]),
               {:ok, %{type: type, mode: mode}} when Bitwise.band(mode, 0o222) == 0 <-
                 File.lstat(path) do
            case type do
              :directory ->
                {:ok, [child | dirs], acc, total}

              :regular ->
                with {:ok, body} <- read(path, min(@max_file, @max_tree - total)) do
                  {:ok, dirs, Map.put(acc, child, sha(body)), total + byte_size(body)}
                end

              _ ->
                :error
            end
          end

        case result do
          {:ok, _, _, _} -> {:cont, result}
          _ -> {:halt, :error}
        end
      end)
      |> case do
        {:ok, dirs, acc, total} -> walk(root, dirs, acc, total, entries + length(names))
        _ -> :error
      end
    end
  end

  defp read(path, limit, write_mask \\ 0o222) do
    with true <- canonical?(path),
         {:ok, before = %{type: :regular, size: size, links: links, mode: mode}}
         when size <= limit and Bitwise.band(mode, write_mask) == 0 and
                (links == 1 or write_mask == 0o022) <- File.lstat(path),
         {:ok, file} <- File.open(path, [:read, :binary]) do
      bytes =
        try do
          if size == 0, do: "", else: IO.binread(file, size + 1)
        after
          File.close(file)
        end

      if is_binary(bytes) and byte_size(bytes) == size and same_file?(path, before),
        do: {:ok, bytes},
        else: :error
    end
  end

  defp same_file?(path, before) do
    case File.lstat(path) do
      {:ok, after_read} -> %{after_read | atime: before.atime} == before
      _ -> false
    end
  end

  defp canonical?(path) when is_binary(path) do
    Path.type(path) == :absolute and Path.expand(path) == path and
      path
      |> Path.split()
      |> Enum.scan(&Path.join(&2, &1))
      |> Enum.all?(fn part ->
        case File.lstat(part) do
          {:ok, %{type: type, mode: mode}} when type in [:regular, :directory] ->
            Bitwise.band(mode, 0o022) == 0

          _ ->
            false
        end
      end)
  end

  defp canonical?(_), do: false

  defp tree_digest(files) do
    files |> Enum.sort() |> Enum.map(fn {path, value} -> [path, 0, value, ?\n] end) |> sha()
  end

  defp digest?(value), do: is_binary(value) and Regex.match?(~r/\A[0-9a-f]{64}\z/, value)

  defp sha(bytes), do: :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)
end
