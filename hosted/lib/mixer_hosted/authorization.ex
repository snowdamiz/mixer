defmodule MixerHosted.Authorization do
  @moduledoc """
  Owns the fresh customer authorization and local SQL transaction.

  The callback must return `{:ok, value}` or `{:error, bounded_reason}` and may
  perform only synchronous local SQL. External effects cannot be rolled back.
  A pure Policy.Decision is never accepted as domain authority. The optional Repo
  argument is trusted server configuration, never request data. No HTTP route
  activates this seam and no caller-supplied clock is accepted.
  """

  alias MixerHosted.Authorization.Policy
  alias MixerHosted.Authorization.Postgres.{Evidence, Session}
  alias MixerHosted.Authorization.Transaction.{Context, Snapshot}

  @errors [
    :invalid_request,
    :unauthenticated,
    :not_found,
    :permission_denied,
    :authorization_unavailable,
    :conflict,
    :immutable_conflict,
    :idempotency_conflict,
    :storage_unavailable
  ]

  @doc "Resolves project-visible metadata, then binds the exact artifact environment in an owned transaction."
  def with_artifact_read_transaction(
        identity,
        project_target,
        manifest_sha256,
        callback,
        repo \\ MixerHosted.Repo
      ) do
    MixerHosted.Authorization.ArtifactRead.run(
      identity,
      project_target,
      manifest_sha256,
      callback,
      repo
    )
  end

  def with_authorized_transaction(identity, action, target, callback, repo \\ MixerHosted.Repo) do
    admitted_at = System.system_time(:second)
    deadline = System.monotonic_time(:millisecond) + 5_000

    with {:ok, scope} <- Policy.request(identity, action, target, admitted_at),
         true <- is_function(callback, 1),
         false <- Context.active?(),
         false <- repo.in_transaction?() do
      lookup = %{identity: Policy.identity_key(identity), action: action, target: scope}

      case repo.transaction(
             fn ->
               try do
                 linkage = Session.prepare!(repo, lookup)
                 evidence = Evidence.load!(repo, lookup, linkage)
                 now = System.system_time(:second)

                 if now < admitted_at or System.monotonic_time(:millisecond) >= deadline,
                   do: repo.rollback(:authorization_unavailable)

                 decision = evaluate!(repo, identity, action, scope, evidence, now)
                 snapshot = Snapshot.load!(repo, identity, evidence, linkage, decision, now)

                 context =
                   Context.bind!(
                     repo,
                     identity,
                     action,
                     scope,
                     evidence,
                     snapshot,
                     admitted_at,
                     deadline
                   )

                 Context.checkpoint!(context, repo, action, scope)

                 case callback.(context) do
                   {:ok, value} ->
                     # The last successful checkpoint is immediately before
                     # returning to Ecto's commit. No user callback follows it.
                     Context.checkpoint!(context, repo, action, scope)
                     {:ok, value}

                   {:error, reason} when reason in @errors ->
                     repo.rollback(reason)

                   _ ->
                     repo.rollback(:authorization_unavailable)
                 end
               after
                 Context.clear!()
               end
             end,
             timeout: 5_000,
             queue: false
           ) do
        {:ok, {:ok, value}} -> {:ok, value}
        {:error, reason} when reason in @errors -> {:error, reason}
        _ -> {:error, :authorization_unavailable}
      end
    else
      {:error, reason} when reason in @errors -> {:error, reason}
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    error ->
      r1370_caught(:error, error)
      {:error, :authorization_unavailable}
  catch
    kind, reason ->
      r1370_caught(kind, reason)
      {:error, :authorization_unavailable}
  end

  defp evaluate!(repo, identity, action, target, evidence, now) do
    case Policy.evaluate(identity, action, target, evidence, now) do
      {:ok, decision} -> decision
      {:error, reason} -> repo.rollback(reason)
    end
  end

  defp r1370_caught(kind, error) do
    key = {:mixer_transaction_minimal_frontier_r1370, :observation}

    case Process.get(key) do
      %{armed: true, first_caught: nil, phase: phase, membership_count: count} = observation
      when phase in [
             nil,
             :authorize,
             :initial_membership_assert,
             :sleep,
             :explicit_checkpoint,
             :fresh_membership_assert,
             :initial_context_assert,
             :ordinary_callback_return
           ] and count in [nil, 0, 1, 2, :"3_to64", :over64] ->
        typeclass =
          case kind do
            :error ->
              case if(is_map(error), do: Map.get(error, :__struct__), else: nil) do
                :"Elixir.ExUnit.AssertionError" -> :assertion_error
                :"Elixir.MixerHosted.Authorization.Transaction.Context.Invalid" -> :context_invalid
                :"Elixir.Postgrex.Error" -> :postgrex_error
                :"Elixir.DBConnection.ConnectionError" -> :db_connection_error
                :"Elixir.MatchError" -> :match_error
                :"Elixir.ArgumentError" -> :argument_error
                :"Elixir.RuntimeError" -> :runtime_error
                _ -> :other_error
              end

            :throw -> :throw
            :exit -> :exit
            _ -> :other_error
          end

        Process.put(key, %{
          observation
          | first_caught: %{typeclass: typeclass, phase: phase, membership_count: count}
        })

      _ -> :ok
    end

    :ok
  rescue
    _ -> :ok
  catch
    _, _ -> :ok
  end
end
