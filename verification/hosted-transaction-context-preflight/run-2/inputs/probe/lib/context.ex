defmodule MixerTransactionContextPreflight.Repo do
  use Ecto.Repo, otp_app: :mixer_transaction_context_preflight, adapter: Ecto.Adapters.Postgres
end

defmodule MixerTransactionContextPreflight.OtherRepo do
  use Ecto.Repo, otp_app: :mixer_transaction_context_preflight, adapter: Ecto.Adapters.Postgres
end

defmodule MixerTransactionContextPreflight.Rejected do
  defexception [:reason]
  def message(%{reason: reason}), do: "preflight context rejected: #{reason}"
end

defmodule MixerTransactionContextPreflight.Context do
  @moduledoc """
  PREIMPLEMENTATION probe only. No membership, authorization, HTTP or product API.
  The arbitrary SQL helper exists solely to exercise this seam with synthetic tables.
  A product repository must expose fixed operations and keep the context internal.
  """

  alias MixerTransactionContextPreflight.{Rejected, Repo}

  defstruct [:owner, :repo, :dynamic_repo, :invocation, :backend_pid, :transaction_id,
             :database, :db_role, :nonce, :deadline_ms, :action, :target]

  @marker {__MODULE__, :active_invocation}
  @nonce_guc "mixer_preflight.invocation_nonce"
  @identity_sql """
  SELECT pg_backend_pid(), pg_current_xact_id()::text, current_database(), current_user,
         current_setting('mixer_preflight.invocation_nonce', true)
  """

  # Exposed only to the adversarial probe; a process-dictionary reference is not a secret.
  def probe_marker_key, do: @marker
  def probe_nonce_guc, do: @nonce_guc

  def enter(fun, budget_ms \\ 5_000) when is_function(fun, 1) do
    reject_if(Process.get(@marker) != nil or Repo.in_transaction?(), :nested_entry)
    reject_if(Repo.get_dynamic_repo() != Repo, :entry_dynamic_repo)
    reject_if(not is_integer(budget_ms) or budget_ms < 1 or budget_ms > 5_000, :invalid_budget)
    deadline = now() + budget_ms

    Repo.transaction(fn ->
      # First SQL statement, before identity lookup or transaction-local GUC reads.
      Repo.query!("SET TRANSACTION ISOLATION LEVEL READ COMMITTED", [], opts(deadline))
      invocation = make_ref()
      nonce = Base.encode16(:crypto.strong_rand_bytes(32), case: :lower)
      Process.put(@marker, invocation)

      try do
        Repo.query!("SELECT set_config($1, $2, true), set_config('lock_timeout', '250ms', true)",
                    [@nonce_guc, nonce], opts(deadline))
        set_budget!(deadline)
        [backend, xid, database, role, ^nonce] = identity!(deadline)

        context = %__MODULE__{
          owner: self(), repo: Repo, dynamic_repo: Repo.get_dynamic_repo(),
          invocation: invocation, backend_pid: backend, transaction_id: xid,
          database: database, db_role: role, nonce: nonce, deadline_ms: deadline,
          action: :synthetic_write, target: {"org-fixture", "project-fixture"}
        }

        result = fun.(context)
        validate!(context, :synthetic_write, {"org-fixture", "project-fixture"})
        result
      after
        Process.delete(@marker)
      end
    end, opts(deadline))
  end

  def query!(context, sql, params \\ [], action \\ :synthetic_write,
             target \\ {"org-fixture", "project-fixture"})
  def query!(%__MODULE__{} = context, sql, params, action, target) do
    validate!(context, action, target)
    # Recalculate after identity verification, immediately before the synthetic effect.
    set_budget!(context.deadline_ms)
    Repo.query!(sql, params, opts(context.deadline_ms))
  end
  def query!(_, _, _, _, _), do: raise(Rejected, reason: :invalid_context)

  def validate!(%__MODULE__{} = context, action, target) do
    reject_if(context.owner != self(), :foreign_process)
    reject_if(context.repo != Repo, :fixed_repo)
    reject_if(context.dynamic_repo != Repo or Repo.get_dynamic_repo() != context.dynamic_repo,
              :dynamic_repo)
    reject_if(not is_reference(context.invocation) or Process.get(@marker) != context.invocation,
              :inactive_invocation)
    reject_if(not Repo.in_transaction?(), :not_in_transaction)
    reject_if(context.action != action or context.target != target, :operation_target)
    remaining!(context.deadline_ms)
    set_budget!(context.deadline_ms)
    [backend, xid, database, role, nonce] = identity!(context.deadline_ms)
    reject_if(backend != context.backend_pid, :backend_changed)
    reject_if(xid != context.transaction_id, :transaction_changed)
    reject_if(database != context.database or role != context.db_role, :database_role_changed)
    reject_if(nonce != context.nonce, :nonce_changed)
    :ok
  end

  def validate!(_, _, _), do: raise(Rejected, reason: :invalid_context)

  defp identity!(deadline), do: Repo.query!(@identity_sql, [], opts(deadline)).rows |> hd()

  defp set_budget!(deadline) do
    remaining = remaining!(deadline)
    Repo.query!("SELECT set_config('statement_timeout', $1, true)",
                [Integer.to_string(remaining) <> "ms"], opts(deadline))
    :ok
  end

  defp opts(deadline), do: [deadline: deadline, timeout: remaining!(deadline), log: false]
  defp remaining!(deadline) when is_integer(deadline) do
    remaining = deadline - now()
    reject_if(remaining <= 0, :deadline_exceeded)
    remaining
  end
  defp remaining!(_), do: raise(Rejected, reason: :invalid_deadline)
  defp now, do: System.monotonic_time(:millisecond)
  defp reject_if(true, reason), do: raise(Rejected, reason: reason)
  defp reject_if(false, _reason), do: :ok
end
