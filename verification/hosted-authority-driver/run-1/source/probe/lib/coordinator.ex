defmodule MixerHosted.AuthorityDriver.Coordinator do
  @moduledoc "Isolated internal specimen. No HTTP, arbitrary SQL callback, domain mutation or public ticket API."
  alias MixerHosted.Repo
  alias MixerHosted.AuthorityDriver.{Rejected, Transport}

  defstruct [
    :owner,
    :repo,
    :dynamic_repo,
    :invocation,
    :identity,
    :target,
    :transaction,
    :deadline_ms,
    :admission,
    :decision
  ]

  @marker {__MODULE__, :active}
  @identity "SELECT pg_backend_pid(),pg_current_xact_id()::text,current_database(),session_user,current_user,current_setting('role'),current_setting('mixer_authz.invocation_nonce',true),current_setting('mixer_authz.deadline',true)::timestamptz,current_setting('transaction_isolation')"
  def marker, do: @marker

  def run(envelope, target, mode \\ :inspect, budget \\ 5_000) do
    reject(Process.get(@marker) != nil or Repo.in_transaction?(), :nested_entry)
    reject(Repo.get_dynamic_repo() != Repo, :dynamic_repo)
    reject(not is_integer(budget) or budget < 1 or budget > 5_000, :invalid_budget)
    i = Transport.identity(envelope)
    t = Transport.target(target)
    deadline = now() + budget

    try do
      Repo.transaction(
        fn ->
          # First post-BEGIN statement. No identity or settings query precedes it.
          Repo.query!("SET TRANSACTION ISOLATION LEVEL READ COMMITTED", [], opts(deadline))
          nonce = Base.encode16(:crypto.strong_rand_bytes(32), case: :lower)

          try do
            Repo.query!(
              "SELECT set_config('mixer_authz.invocation_nonce',$1,true),set_config('mixer_authz.deadline',(clock_timestamp()+$2::int4*interval '1 millisecond')::text,true),set_config('lock_timeout','250ms',true)",
              [nonce, remaining!(deadline)],
              opts(deadline)
            )

            set_budget!(deadline)

            [pid, xid, db, role, ^role, "none", ^nonce, dbdeadline, "read committed"] =
              actual!(deadline)

            reject(
              role! = "mixer_hosted_runtime" or db! = "authority_contract",
              :runtime_identity
            )

            c = %__MODULE__{
              owner: self(),
              repo: Repo,
              dynamic_repo: Repo,
              invocation: make_ref(),
              identity: i,
              target: t,
              transaction: %{
                backend: pid,
                full_xid: xid,
                database_name: db,
                runtime_role: role,
                nonce: nonce,
                deadline: dbdeadline
              },
              deadline_ms: deadline
            }

            activate(c)
            a = call(c, :lookup)
            c = activate(%{c | admission: a})
            a = call(c, :lock)
            c = activate(%{c | admission: a})
            d = call(c, :decision)
            c = activate(%{c | decision: d})
            if d.outcome! = "allowed", do: Repo.rollback({:denied, d.outcome})
            result = MixerHosted.AuthorityDriver.FixtureCallback.run(mode, c)
            validate!(c, c.target)
            result
          after
            Process.delete(@marker)
          end
        end,
        opts(deadline)
      )
    rescue
      e in Postgrex.Error -> raise Rejected, reason: {:database, e.postgres[:pg_code]}
      _e in DBConnection.ConnectionError -> raise Rejected, reason: :storage_unavailable
    after
      Process.delete(@marker)
    end
  end

  def validate!(%__MODULE__{} = c, target) do
    reject(c.owner! = self(), :foreign_process)
    reject(c.repo! = Repo, :fixed_repo)
    reject(c.dynamic_repo! = Repo or Repo.get_dynamic_repo() != Repo, :dynamic_repo)
    reject(Process.get(@marker) != c, :inactive_or_changed_context)
    reject(c.target! = target, :target)
    reject(not Repo.in_transaction?(), :not_transaction)
    remaining!(c.deadline_ms)
    set_budget!(c.deadline_ms)

    [pid, xid, db, srole, role, role_setting, nonce, dbdeadline, isolation] =
      actual!(c.deadline_ms)

    reject(
      [pid, xid, db, srole, nonce, dbdeadline] != [
        c.transaction.backend,
        c.transaction.full_xid,
        c.transaction.database_name,
        c.transaction.runtime_role,
        c.transaction.nonce,
        c.transaction.deadline
      ] or role! = srole or role_setting! = "none" or isolation! = "read committed",
      :transaction_changed
    )

    # DB clock is checked independently of original monotonic budget; neither is refreshed.
    [[true]] =
      Repo.query!(
        "SELECT clock_timestamp() < $1::timestamptz",
        [c.transaction.deadline],
        opts(c.deadline_ms)
      ).rows

    :ok
  end

  def validate!(_, _), do: raise(Rejected, reason: :invalid_context)
  # Narrow synthetic effect only; no caller SQL, customer callback or domain data.
  def synthetic_effect!(c) do
    validate!(c, c.target)
    set_budget!(c.deadline_ms)

    Repo.query!(
      "INSERT INTO driver_fixture.effects(invocation) VALUES ($1)",
      [c.transaction.nonce],
      opts(c.deadline_ms)
    )

    :ok
  end

  defp call(c, stage) do
    validate!(c, c.target)
    set_budget!(c.deadline_ms)

    result =
      Repo.query!(
        Transport.query(stage),
        Transport.params(
          c.identity,
          c.target,
          c.transaction,
          if(stage == :lookup, do: nil, else: c.admission)
        ),
        opts(c.deadline_ms)
      )

    if stage == :decision,
      do: Transport.decision(result, c.admission),
      else: Transport.admission(result, c.identity, c.target, c.transaction, stage)
  end

  defp activate(c),
    do:
      (
        Process.put(@marker, c)
        c
      )

  defp actual!(d), do: Repo.query!(@identity, [], opts(d)).rows |> hd()

  defp set_budget!(d),
    do:
      Repo.query!(
        "SELECT set_config('statement_timeout',$1,true)",
        [Integer.to_string(remaining!(d)) <> "ms"],
        opts(d)
      )

  defp opts(d), do: [deadline: d, timeout: remaining!(d), queue: false, log: false]

  defp remaining!(d) do
    r = d - now()
    reject(r <= 0, :deadline_exceeded)
    r
  end

  defp now, do: System.monotonic_time(:millisecond)
  defp reject(true, r), do: raise(Rejected, reason: r)
  defp reject(false, _), do: :ok
end
