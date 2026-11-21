defmodule MixerHosted.Authorization do
  @moduledoc """
  Owns the fresh customer authorization and local SQL transaction.

  The callback must return `{:ok, value}` or `{:error, bounded_reason}` and may
  perform only synchronous local SQL. A release publication may return
  `{:ok, value, {:valid_during, start, expiry}}` to bind commit to an inclusive
  start and exclusive expiry in Unix seconds. Use `nil` for unbounded expiry.
  External effects cannot be rolled back.
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
    :scope_denied,
    :release_not_found,
    :not_validated,
    :assignment_rejected,
    :invalid_promotion,
    :invalid_rollback,
    :invalid_halt,
    :stale_rollout,
    :artifact_invalid,
    :unknown_runtime,
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
                 if action == "build.create" do
                   Session.query!(repo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

                   MixerHosted.BrowserAuth.ActiveCreate.check_current!(%{
                     repo: repo,
                     identity: identity
                   })
                 end

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
                     commit_value!(context, repo, action, scope, value, {0, nil})

                   {:ok, value, {:valid_during, start, expiry}}
                   when action == "release.publish" and is_integer(start) and start >= 0 and
                          (is_nil(expiry) or (is_integer(expiry) and expiry > start)) ->
                     commit_value!(context, repo, action, scope, value, {start, expiry})

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
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp commit_value!(context, repo, action, scope, value, {start, expiry}) do
    # Use the same fresh authority checkpoint for domain validity and the SQL commit.
    %{checked_at: now} = Context.checkpoint!(context, repo, action, scope)

    if now < start or (expiry != nil and now >= expiry),
      do: repo.rollback(:assignment_rejected)

    if action == "build.create",
      do: MixerHosted.BrowserAuth.ActiveCreate.check_current!(context)

    {:ok, value}
  end

  defp evaluate!(repo, identity, action, target, evidence, now) do
    case Policy.evaluate(identity, action, target, evidence, now) do
      {:ok, decision} -> decision
      {:error, reason} -> repo.rollback(reason)
    end
  end
end
