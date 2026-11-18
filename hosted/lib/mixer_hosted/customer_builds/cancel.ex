defmodule MixerHosted.CustomerBuilds.Cancel do
  @moduledoc false
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.BrowserAuth.ActiveCreate
  alias MixerHosted.CustomerBuilds.{CancelSchema, CreateRepo, CreateSchema, Selection, Snapshot}
  alias MixerHosted.RuntimeConfig

  @action "build.create"

  def run(identity, input) do
    with true <- RuntimeConfig.build_cancel_enabled?(),
         {:ok, selection} <- Selection.new(input) do
      target = Map.take(selection, [:organization_id, :project_id, :application_id])

      MixerHosted.Authorization.with_authorized_transaction(
        identity,
        @action,
        target,
        fn c ->
          Context.effect!(c, CreateRepo, @action, c.target, fn _ ->
            CreateSchema.admit!(CreateRepo, :builds_v1)
            CancelSchema.admit!(CreateRepo)
            ActiveCreate.require_browser_current!(c)

            [result] =
              Session.one!(
                CreateRepo,
                "SELECT public.mixer_customer_build_cancel_v1($1,$2,$3,$4,$5)",
                [
                  selection.build_id,
                  selection.platform,
                  selection.source_sha256,
                  selection.toolchain_lock_sha256,
                  selection.build_definition_sha256
                ],
                :storage_unavailable
              )

            Context.checkpoint!(c, CreateRepo, @action, c.target)
            ActiveCreate.require_browser_current!(c)
            project(result, selection)
          end)
        end,
        CreateRepo
      )
    else
      false -> {:error, :not_found}
      error -> error
    end
  end

  defp project(nil, _), do: {:error, :not_found}
  defp project(%{"outcome" => "conflict"}, _), do: {:error, :conflict}

  defp project(%{"outcome" => outcome, "record" => record}, selection)
       when outcome in ["applied", "duplicate"] do
    row =
      Map.new(
        ~w(id organization_id project_id application_id build_id platform request_key revision journal)a,
        &{&1, Map.fetch!(record, Atom.to_string(&1))}
      )

    case Snapshot.project(row, selection) do
      {:ok, %{state: state} = build} when state in ["cancelling", "cancelled"] ->
        {:ok, %{outcome: outcome, build: build}}

      _ ->
        CreateRepo.rollback(:storage_unavailable)
    end
  end

  defp project(_, _), do: CreateRepo.rollback(:storage_unavailable)
end
