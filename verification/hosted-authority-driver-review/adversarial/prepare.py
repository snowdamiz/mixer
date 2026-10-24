#!/usr/bin/env python3
import pathlib,shutil,hashlib,json
here=pathlib.Path(__file__).resolve().parents[1]
src=here/'frozen-run'; dest=here/'adversarial-input'
assert not dest.exists();shutil.copytree(src,dest)
callback=dest/'source/probe/lib/fixture_callback.ex'
b=callback.read_text()
extra='''
  # Review-only closed fixture modes; unchanged frozen coordinator and transport.
  defp execute(:review_equal_floats, c) do
    changes = [
      {"identity.profile_version", %{c | identity: %{c.identity | profile_version: c.identity.profile_version / 1}}},
      {"identity.issued_at", %{c | identity: %{c.identity | issued_at: c.identity.issued_at / 1}}},
      {"identity.expires_at", %{c | identity: %{c.identity | expires_at: c.identity.expires_at / 1}}},
      {"identity.authentication_completed_at", %{c | identity: %{c.identity | authentication_completed_at: c.identity.authentication_completed_at / 1}}},
      {"admission.profile_revision", %{c | admission: %{c.admission | profile_revision: c.admission.profile_revision / 1}}},
      {"decision.project_revision", %{c | decision: %{c.decision | project_revision: c.decision.project_revision / 1}}},
      {"decision.memberships.revision", %{c | decision: %{c.decision | memberships: Enum.map(c.decision.memberships, &%{&1 | revision: &1.revision / 1})}}},
      {"transaction.backend", %{c | transaction: %{c.transaction | backend: c.transaction.backend / 1}}}
    ]
    results = for {field, copy} <- changes do
      try do
        Coordinator.synthetic_effect!(copy)
        %{field: field, strict_equal_original: copy === c, loose_equal_original: copy == c, accepted: true, effect_issued: true}
      rescue
        e -> %{field: field, strict_equal_original: copy === c, loose_equal_original: copy == c, accepted: false, error: Exception.message(e)}
      end
    end
    Agent.update(DriverEvidence, &put_in(&1, [:observations, :equal_float_substitutions], results))
    c
  end

  defp execute(:review_old_context, c) do
    old = Process.fetch!(:review_old_context)
    e = assert_raise Rejected, fn -> Coordinator.synthetic_effect!(old) end
    assert e.reason == :inactive_or_changed_context
    c
  end

  defp execute(:review_deadline_guc, c) do
    MixerHosted.Repo.query!("SELECT set_config('mixer_authz.deadline',($1::timestamptz+interval '1 second')::text,true)", [c.transaction.deadline], log: false)
    Coordinator.synthetic_effect!(c)
  end

  defp execute(:review_statement_guc, c) do
    MixerHosted.Repo.query!("SELECT set_config('statement_timeout','0',true)", [], log: false)
    Coordinator.validate!(c, c.target)
    [[timeout]] = MixerHosted.Repo.query!("SELECT setting::int FROM pg_settings WHERE name='statement_timeout'", [], log: false).rows
    assert timeout > 0 and timeout <= 5_000
    c
  end

  defp execute(:review_rollback_rebegin, c) do
    MixerHosted.Repo.query!("ROLLBACK", [], log: false)
    MixerHosted.Repo.query!("BEGIN", [], log: false)
    MixerHosted.Repo.query!("SELECT set_config('mixer_authz.invocation_nonce',$1,true),set_config('mixer_authz.deadline',$2::timestamptz::text,true)", [c.transaction.nonce,c.transaction.deadline], log: false)
    e = assert_raise Rejected, fn -> Coordinator.synthetic_effect!(c) end
    assert e.reason == :transaction_changed
    c
  end

'''
assert '  defp execute(:hold, c)' in b
callback.write_text(b.replace('  defp execute(:hold, c)',extra+'  defp execute(:hold, c)',1))
driver=dest/'source/probe/driver_test.exs'; b=driver.read_text()
ending='DriverTests.run()\nSupervisor.stop(repo)\nGenServer.stop(owner)\n';assert b.endswith(ending)
review=(here/'adversarial/review_test.exs').read_text()
driver.write_text(b[:-len(ending)]+review+'\nReviewTests.run()\nSupervisor.stop(repo)\nGenServer.stop(owner)\n')
print(json.dumps({'unchanged_core':{p:hashlib.sha256((dest/'source/probe/lib'/p).read_bytes()).hexdigest() for p in ['coordinator.ex','transport.ex']},'fixture':'review-only fixed fixture modes','tests':'independent bounded cases; producer DriverTests helper setup reused, original cases not run'}))
