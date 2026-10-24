defmodule MixerHosted.AuthorityDriver.FixtureCallback do
  import ExUnit.Assertions
  alias MixerHosted.AuthorityDriver.{Coordinator, Rejected}
  alias MixerHosted.Repo

  def run(mode, c) do
    Agent.update(DriverEvidence, fn s -> %{s | callback_entries: s.callback_entries + 1} end)
    execute(mode, c)
  end

  defp execute(:hold, c) do
    parent = Process.get(:hold_fixture)
    send(parent, {:allowed, self(), c})

    receive do
      :release -> :ok
    after
      1_000 -> raise "hold release timeout"
    end

    Coordinator.synthetic_effect!(c)
    c
  end

  defp execute(:inspect, c), do: c

  defp execute(:effect, c),
    do:
      (
        Coordinator.synthetic_effect!(c)
        c
      )

  defp execute(:rollback, c),
    do:
      (
        Process.put(:captured, c)
        Coordinator.synthetic_effect!(c)
        Repo.rollback(:fixture)
      )

  defp execute(:exception, c),
    do:
      (
        Process.put(:captured, c)
        Coordinator.synthetic_effect!(c)
        raise "fixture exception"
      )

  defp execute(:credential_overrun, c),
    do:
      (
        Coordinator.synthetic_effect!(c)
        Process.sleep(150)
        c
      )

  defp execute(:overrun, c),
    do:
      (
        Coordinator.synthetic_effect!(c)
        Process.sleep(330)
        c
      )

  defp execute(:slow_sql, c),
    do:
      (
        Coordinator.synthetic_effect!(c)
        Repo.query!("SELECT pg_sleep(0.8)", [], log: false)
        c
      )

  defp execute(:nonce, c) do
    Repo.query!("SELECT set_config('mixer_authz.invocation_nonce','changed',true)", [],
      log: false
    )

    Coordinator.synthetic_effect!(c)
  end

  defp execute(:raw_rebegin, c) do
    Repo.query!("COMMIT", [], log: false)
    Repo.query!("BEGIN", [], log: false)

    Repo.query!(
      "SELECT set_config('mixer_authz.invocation_nonce',$1,true),set_config('mixer_authz.deadline',$2::timestamptz::text,true)",
      [c.transaction.nonce, c.transaction.deadline], log: false)

    e = assert_raise Rejected, fn -> Coordinator.synthetic_effect!(c) end
    assert e.reason == :transaction_changed
    c
  end

  defp execute(:tamper, c) do
    copies = [
      %{c | deadline_ms: c.deadline_ms + 1},
      %{c | deadline_ms: c.deadline_ms - 1},
      %{
        c
        | transaction: %{
            c.transaction
            | deadline: DateTime.add(c.transaction.deadline, 1, :microsecond)
          }
      },
      %{c | target: %{c.target | environment: "prod"}},
      %{c | identity: %{c.identity | subject: "other"}},
      %{
        c
        | identity: %{
            c.identity
            | authentication_completed_at: c.identity.authentication_completed_at + 1
          }
      },
      %{c | decision: %{c.decision | project_revision: c.decision.project_revision + 1}},
      %{c | decision: %{c.decision | memberships: []}},
      %{c | admission: %{c.admission | family_id: <<0::128>>}},
      %{c | invocation: make_ref()}
    ]

    for copy <- copies, do: assert_raise(Rejected, fn -> Coordinator.synthetic_effect!(copy) end)
    exact = struct(Coordinator, Map.from_struct(c))
    assert Coordinator.validate!(exact, c.target) == :ok

    e =
      Task.async(fn -> assert_raise Rejected, fn -> Coordinator.synthetic_effect!(c) end end)
      |> Task.await(1_000)

    assert e.reason == :foreign_process

    e =
      assert_raise Rejected, fn ->
        Coordinator.synthetic_effect!(%{c | repo: DriverFixtureOwner})
      end

    assert e.reason == :fixed_repo
    old = Repo.put_dynamic_repo(DriverFixtureOwner)

    try do
      assert_raise Rejected, fn -> Coordinator.synthetic_effect!(c) end
    after
      Repo.put_dynamic_repo(old)
    end

    assert_raise Rejected, fn -> Coordinator.run(nil, c.target) end
    assert_raise Rejected, fn -> Coordinator.validate!(c, %{c.target | project: "q"}) end
    c
  end

  defp execute(:budget, c) do
    first =
      Repo.query!("SELECT setting::int FROM pg_settings WHERE name='statement_timeout'", [],
        log: false
      ).rows

    Process.sleep(35)
    Coordinator.validate!(c, c.target)

    second =
      Repo.query!("SELECT setting::int FROM pg_settings WHERE name='statement_timeout'", [],
        log: false
      ).rows

    assert second < first

    Agent.update(
      DriverEvidence,
      &put_in(&1, [:observations, :budgets], %{
        first: first,
        second: second,
        dbdeadline: DateTime.to_iso8601(c.transaction.deadline)
      })
    )

    c
  end
end
