defmodule MixerHosted.CustomerBuilds.Create do
  @moduledoc false
  alias MixerHosted.CustomerBuilds.{CreateInput, CreateRepo, CreateSchema}
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Builds.{Storage, Coordinator}

  def run(identity, input, key) do
    with {:ok, i} <- CreateInput.new(input), true <- CreateInput.id?(key) do
      target = Map.take(i, [:organization_id, :project_id, :application_id])

      MixerHosted.Authorization.with_authorized_transaction(
        identity,
        "build.create",
        target,
        fn c ->
          Context.effect!(c, CreateRepo, "build.create", c.target, fn _ ->
            CreateSchema.admit!(
              CreateRepo,
              MixerHosted.RuntimeConfig.installed_processor_profile()
            )

            MixerHosted.BrowserAuth.ActiveCreate.check_current!(c)

            rows =
              Session.query!(
                CreateRepo,
                """
                SELECT source_sha256,toolchain_lock_sha256,build_definition_sha256,source_kind,source_reference,max_attempts,timeout_ms,retry_backoff_ms
                FROM public.mixer_customer_build_inputs WHERE organization_id=$1 AND project_id=$2 AND application_id=$3 AND platform=$4 AND input_id=$5
                """,
                [
                  i.organization_id,
                  i.project_id,
                  i.application_id,
                  Atom.to_string(i.platform),
                  i.source_input_id
                ]
              ).rows

            case rows do
              [] ->
                {:error, :not_found}

              [[source, tool, definition, kind, reference, attempts, timeout, backoff]] ->
                if {source, tool, definition} !=
                     {i.source_sha256, i.toolchain_lock_sha256, i.build_definition_sha256} do
                  {:error, :idempotency_conflict}
                else
                  spec =
                    target
                    |> Map.merge(%{
                      build_id: CreateInput.build_id(i, key),
                      platform: i.platform,
                      source: %{
                        kind: if(kind == "upload", do: :upload, else: :revision),
                        sha256: source,
                        reference: reference
                      },
                      toolchain_lock_sha256: tool,
                      build_definition_sha256: definition
                    })

                  policy = %{
                    max_attempts: attempts,
                    timeout_ms: timeout,
                    retry_backoff_ms: backoff
                  }

                  multi =
                    Storage.create_multi(
                      Ecto.Multi.new(),
                      :build,
                      spec,
                      policy,
                      key,
                      System.system_time(:millisecond),
                      fn intent ->
                        Context.checkpoint!(c, CreateRepo, "build.create", c.target)
                        Coordinator.new(intent)
                      end
                    )

                  case CreateRepo.transaction(multi) do
                    {:ok, %{build: r}} ->
                      Context.checkpoint!(c, CreateRepo, "build.create", c.target)
                      MixerHosted.BrowserAuth.ActiveCreate.check_current!(c)

                      selection =
                        spec
                        |> Map.take([
                          :organization_id,
                          :project_id,
                          :application_id,
                          :build_id,
                          :platform,
                          :toolchain_lock_sha256,
                          :build_definition_sha256
                        ])
                        |> Map.put(:source_sha256, source)

                      {:ok,
                       %{
                         outcome: r.outcome,
                         selection: selection,
                         state: r.build.state,
                         revision: r.record.revision
                       }}

                    {:error, _, :idempotency_conflict, _} ->
                      {:error, :idempotency_conflict}

                    {:error, _, :build_conflict, _} ->
                      {:error, :conflict}

                    _ ->
                      {:error, :storage_unavailable}
                  end
                end
            end
          end)
        end,
        CreateRepo
      )
    else
      _ -> {:error, :invalid_request}
    end
  end
end
