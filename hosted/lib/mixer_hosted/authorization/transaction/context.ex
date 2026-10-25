defmodule MixerHosted.Authorization.Transaction.Context do
  @moduledoc """
  Request-local trusted API discipline for a live owned SQL transaction.

  Contexts are checked by complete equality against one bounded owner-process
  binding and by the actual connection, transaction and transaction-local marker.
  Structs and the process dictionary are not a sandbox against malicious BEAM
  code. A returned or copied context is not a reusable authorization ticket.
  """

  alias MixerHosted.Authorization.Policy
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Snapshot

  @key {__MODULE__, :active}
  @required_scopes %{
    "artifact.read" => "mixer.artifact.read",
    "artifact.upload" => "mixer.artifact.upload",
    "audit.read" => "mixer.audit.read"
  }
  @effect_errors [
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
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase)
  @enforce_keys [
    :owner,
    :repo,
    :dynamic_repo,
    :connection,
    :marker,
    :identity,
    :action,
    :target,
    :snapshot,
    :admitted_at,
    :deadline
  ]
  defstruct @enforce_keys

  defmodule Invalid do
    defexception message: "authorization context is unavailable"
  end

  @doc false
  def active?, do: not is_nil(Process.get(@key))

  @doc false
  def clear!, do: Process.delete(@key)

  @doc false
  def bind!(repo, identity, action, target, evidence, snapshot, admitted_at, deadline) do
    if active?(), do: fail!()
    marker = Base.encode16(:crypto.strong_rand_bytes(32), case: :lower)

    Session.context!(repo,
      action: action,
      transaction_marker: marker,
      token_issued_at: Integer.to_string(identity.issued_at),
      token_expires_at: Integer.to_string(identity.expires_at),
      required_scope: Map.fetch!(@required_scopes, action),
      phase: "effect"
    )

    context = %__MODULE__{
      owner: self(),
      repo: repo,
      dynamic_repo: repo.get_dynamic_repo(),
      connection: connection!(repo),
      marker: marker,
      identity: identity,
      action: action,
      target: target,
      snapshot: snapshot,
      admitted_at: admitted_at,
      deadline: deadline
    }

    Process.put(@key, %{
      context: context,
      evidence: evidence,
      last_time: snapshot.checked_at,
      failed: false
    })

    context
  end

  @doc "Freshly checks the exact live transaction after any later domain lock wait."
  def checkpoint!(context, repo, action, target) do
    case Process.get(@key) do
      %{context: bound, evidence: evidence, last_time: previous, failed: false} = state
      when context === bound and bound.owner == self() and bound.repo == repo and
             bound.action == action and bound.target === target ->
        if repo.get_dynamic_repo() != bound.dynamic_repo or not repo.in_transaction?() or
             System.monotonic_time(:millisecond) >= bound.deadline or
             connection!(repo) !== bound.connection do
          fail!()
        end

        snapshot = fresh_snapshot!(bound, evidence, action, target, previous, 2)
        Process.put(@key, %{state | last_time: snapshot.checked_at})
        snapshot

      _ ->
        fail!()
    end
  rescue
    error in Invalid -> reraise error, __STACKTRACE__
    _ -> fail!()
  catch
    # Preserve Ecto's rollback throw; mark failures before issuing it below.
    kind, reason -> :erlang.raise(kind, reason, __STACKTRACE__)
  end

  @doc """
  Checks immediately before synchronous local SQL; never call remote services.

  An escaped exception/throw/exit or an explicit `{:error, reason}` return
  latches failure and rolls back, even if the outer callback catches it.
  Other local SQL/snapshot return values are passed through unchanged.
  """
  def effect!(context, repo, action, target, callback) when is_function(callback, 1) do
    snapshot = checkpoint!(context, repo, action, target)

    result =
      try do
        callback.(snapshot)
      rescue
        _ -> fail!()
      catch
        _, _ -> fail!()
      end

    case result do
      {:error, reason} when reason in @effect_errors -> fail!(reason)
      {:error, _} -> fail!()
      value -> value
    end
  end

  def effect!(_, _, _, _, _), do: fail!()

  defp fresh_snapshot!(bound, evidence, action, target, previous, remaining) do
    now = System.system_time(:second)

    if now < bound.admitted_at or now < previous or
         System.monotonic_time(:millisecond) >= bound.deadline,
       do: fail!()

    case Policy.evaluate(bound.identity, action, target, evidence, now) do
      {:ok, decision} ->
        # An expired grant may disappear while another locked grant still permits
        # the action. The initial snapshot in the Context remains immutable.
        memberships =
          evidence.memberships
          |> Enum.filter(&(&1.id in decision.membership_ids))
          |> Enum.sort_by(& &1.id)

        snapshot = %{bound.snapshot | checked_at: now, memberships: memberships}
        if not Snapshot.valid?(snapshot, bound.identity, decision), do: fail!()

        # Validation may be descheduled. Do not return a check whose deadline or
        # temporal evidence expired during evaluation. A second boundary change
        # fails closed rather than introducing an unbounded retry loop.
        final_time = System.system_time(:second)

        if final_time < now or System.monotonic_time(:millisecond) >= bound.deadline,
          do: fail!()

        cond do
          final_time == now -> snapshot
          remaining > 1 -> fresh_snapshot!(bound, evidence, action, target, now, remaining - 1)
          true -> fail!()
        end

      {:error, reason} ->
        fail!(reason)
    end
  end

  defp connection!(repo) do
    fields =
      Enum.map_join(@settings, ",", &"pg_catalog.current_setting('mixer.authz.#{&1}', true)")

    case Session.query!(
           repo,
           "SELECT pg_catalog.pg_backend_pid(), pg_catalog.pg_current_xact_id()::text, current_user::text, session_user::text, " <>
             fields
         ).rows do
      [row] -> row
      _ -> fail!()
    end
  end

  defp fail!(reason \\ :authorization_unavailable) do
    case Process.get(@key) do
      %{context: bound} = state ->
        Process.put(@key, %{state | failed: true})

        if bound.owner == self() and bound.repo.get_dynamic_repo() == bound.dynamic_repo and
             bound.repo.in_transaction?(),
           do: bound.repo.rollback(reason)

        raise Invalid

      _ ->
        raise Invalid
    end
  end
end
