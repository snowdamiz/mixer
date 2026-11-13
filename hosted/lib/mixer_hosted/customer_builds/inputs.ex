defmodule MixerHosted.CustomerBuilds.Inputs do
  @moduledoc "Read-only projection of admitted inputs, under current create authority."
  alias MixerHosted.CustomerBuilds.{CreateInput, CreateRepo, CreateSchema}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  @scope [:organization_id, :project_id, :application_id]
  @names %{
    "organization_id" => :organization_id,
    "project_id" => :project_id,
    "application_id" => :application_id,
    "cursor" => :cursor
  }

  def parse(raw) when is_binary(raw) and byte_size(raw) in 1..8192 do
    pairs = :binary.split(raw, "&", [:global])

    with true <- length(pairs) in 3..4,
         {:ok, values} <-
           Enum.reduce_while(pairs, {:ok, %{}}, fn pair, {:ok, acc} ->
             case :binary.split(pair, "=") do
               [key, value] ->
                 name = @names[key]

                 if name != nil and not Map.has_key?(acc, name) and byte_size(value) in 1..4200 and
                      not Regex.match?(~r/%(?![0-9a-fA-F]{2})/, value) do
                   decoded = URI.decode_www_form(value)

                   if URI.encode_www_form(decoded) == value,
                     do: {:cont, {:ok, Map.put(acc, name, decoded)}},
                     else: {:halt, :error}
                 else
                   {:halt, :error}
                 end

               _ ->
                 {:halt, :error}
             end
           end),
         {:ok, input} <- new(Map.delete(values, :cursor), values[:cursor]) do
      {:ok, input}
    else
      _ -> {:error, :invalid_request}
    end
  rescue
    _ -> {:error, :invalid_request}
  end

  def parse(_), do: {:error, :invalid_request}

  def new(scope, cursor) when is_map(scope) and not is_struct(scope) do
    with true <- Enum.sort(Map.keys(scope)) == Enum.sort(@scope),
         true <- Enum.all?(@scope, &CreateInput.id?(scope[&1])),
         {:ok, last} <- decode(scope, cursor) do
      {:ok, %{scope: scope, last: last}}
    else
      _ -> {:error, :invalid_request}
    end
  end

  def new(_, _), do: {:error, :invalid_request}

  def cursor(scope, [platform, id]),
    do: Base.url_encode64(bytes(scope, [platform, id]), padding: false)

  defp decode(_, nil), do: {:ok, nil}

  defp decode(scope, cursor) when is_binary(cursor) and byte_size(cursor) in 1..1400 do
    with {:ok, raw} <- Base.url_decode64(cursor, padding: false),
         true <- byte_size(raw) <= 1024,
         {:ok, parsed} when is_map(parsed) <- Jason.decode(raw),
         last = [parsed["lastPlatform"], parsed["lastSourceInputId"]],
         [platform, id] = last,
         true <- platform in ["ios", "android"] and CreateInput.id?(id),
         ^raw <- bytes(scope, last),
         ^cursor <- Base.url_encode64(raw, padding: false) do
      {:ok, last}
    else
      _ -> {:error, :invalid_request}
    end
  end

  defp decode(_, _), do: {:error, :invalid_request}

  defp bytes(scope, [platform, id]) do
    pairs = [
      {"v", 1},
      {"kind", "build_inputs"},
      {"organizationId", scope.organization_id},
      {"projectId", scope.project_id},
      {"applicationId", scope.application_id},
      {"lastPlatform", platform},
      {"lastSourceInputId", id}
    ]

    "{" <>
      Enum.map_join(pairs, ",", fn {k, v} -> Jason.encode!(k) <> ":" <> Jason.encode!(v) end) <>
      "}"
  end

  def run(identity, %{scope: scope, last: last} = input) when map_size(input) == 2 do
    # Re-parse the private operation as well: a continuation carries no authority.
    with {:ok, ^input} <- new(scope, if(last == nil, do: nil, else: cursor(scope, last))) do
      MixerHosted.Authorization.with_authorized_transaction(
        identity,
        "build.create",
        scope,
        fn c ->
          Context.effect!(c, CreateRepo, "build.create", c.target, fn _ ->
            CreateSchema.admit!(CreateRepo)
            MixerHosted.BrowserAuth.ActiveCreate.require_browser_current!(c)

            {predicate, params} =
              case last do
                nil ->
                  {"", []}

                [platform, id] ->
                  {" AND (platform COLLATE \"C\", input_id COLLATE \"C\") > ($4::text COLLATE \"C\", $5::text COLLATE \"C\")",
                   [platform, id]}
              end

            rows =
              Session.query!(
                CreateRepo,
                """
                SELECT platform,input_id,source_sha256,toolchain_lock_sha256,build_definition_sha256
                FROM public.mixer_customer_build_inputs
                WHERE organization_id=$1 AND project_id=$2 AND application_id=$3
                """ <>
                  predicate <> " ORDER BY platform COLLATE \"C\", input_id COLLATE \"C\" LIMIT 26",
                [scope.organization_id, scope.project_id, scope.application_id] ++ params
              ).rows

            result = project(scope, rows)
            Context.checkpoint!(c, CreateRepo, "build.create", c.target)
            MixerHosted.BrowserAuth.ActiveCreate.require_browser_current!(c)
            result
          end)
        end,
        CreateRepo
      )
    else
      _ -> {:error, :invalid_request}
    end
  end

  def run(_, _), do: {:error, :invalid_request}

  def project(scope, rows) when is_list(rows) and length(rows) <= 26 do
    with {:ok, inputs} <-
           Enum.reduce_while(rows, {:ok, []}, fn row, {:ok, acc} ->
             case project_row(scope, row) do
               {:ok, item} -> {:cont, {:ok, [item | acc]}}
               _ -> {:halt, {:error, :storage_unavailable}}
             end
           end) do
      inputs = inputs |> Enum.reverse() |> Enum.take(25)
      last = List.last(inputs)

      {:ok,
       %{
         organizationId: scope.organization_id,
         projectId: scope.project_id,
         applicationId: scope.application_id,
         inputs: inputs,
         nextCursor:
           if(length(rows) > 25,
             do: cursor(scope, [last.platform, last.sourceInputId]),
             else: nil
           )
       }}
    end
  end

  def project(_, _), do: {:error, :storage_unavailable}

  defp project_row(scope, [platform, id, source, tool, definition])
       when platform in ["ios", "android"] do
    input =
      Map.merge(scope, %{
        platform: if(platform == "ios", do: :ios, else: :android),
        source_input_id: id,
        source_sha256: source,
        toolchain_lock_sha256: tool,
        build_definition_sha256: definition
      })

    with {:ok, _} <- CreateInput.new(input) do
      {:ok,
       %{
         platform: platform,
         sourceInputId: id,
         sourceSha256: source,
         toolchainLockSha256: tool,
         buildDefinitionSha256: definition
       }}
    end
  end

  defp project_row(_, _), do: {:error, :storage_unavailable}
end
