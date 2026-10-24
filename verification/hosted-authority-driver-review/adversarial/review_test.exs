defmodule ReviewTests do
  import ExUnit.Assertions
  alias MixerHosted.AuthorityDriver.{Coordinator, Transport, Rejected}
  alias MixerHosted.Repo
  alias DriverTests, as: F

  defp reject(fun), do: F.rejected(fun)

  defp early_second do
    s=F.scalar("SELECT floor(extract(epoch FROM clock_timestamp()))") |> Transport.integer!()
    n=System.system_time(:millisecond)
    if rem(n,1_000)>150, do: Process.sleep(1_015-rem(n,1_000))
    F.scalar("SELECT floor(extract(epoch FROM clock_timestamp()))") |> Transport.integer!()
  end

  def cases do
    [
      {"reproduce exact-context equal-float type substitution and committed effects", fn ->
        {e,t}=F.seed()
        assert {:ok,_}=Coordinator.run(e,t,:review_equal_floats)
        probes=Agent.get(DriverEvidence,& &1.observations.equal_float_substitutions)
        assert length(probes)==8
        assert Enum.all?(probes,&(&1.accepted and &1.effect_issued and &1.loose_equal_original and not &1.strict_equal_original))
        assert F.scalar("SELECT count(*) FROM driver_fixture.effects")==8
        F.observe(:equal_float_contract, %{contract_passed: false, reproduced: true, committed_effects: 8, fields: Enum.map(probes,& &1.field), authority_value_changed: false})
      end},
      {"old exact original context rejected during later active invocation", fn ->
        {e,t}=F.seed(); assert {:ok,c}=Coordinator.run(e,t)
        Process.put(:review_old_context,c)
        try do assert {:ok,_}=Coordinator.run(e,t,:review_old_context)
        after Process.delete(:review_old_context) end
        F.no_effects()
      end},
      {"database deadline GUC cannot extend unchanged context", fn ->
        {e,t}=F.seed();F.rejected(fn -> Coordinator.run(e,t,:review_deadline_guc) end,true)
      end},
      {"statement timeout reset to zero is overwritten by guard", fn ->
        {e,t}=F.seed(); assert {:ok,_}=Coordinator.run(e,t,:review_statement_guc); F.no_effects()
      end},
      {"raw ROLLBACK BEGIN restored nonce/deadline rejects actual full xid", fn ->
        {e,t}=F.seed(); F.rejected(fn -> Coordinator.run(e,t,:review_rollback_rebegin) end,true)
      end},
      {"original completion age45 exact lower window is inclusive", fn ->
        {e,t}=F.seed();now=early_second();e=%{e|authentication_completed_at: now-45}
        assert {:ok,c}=Coordinator.run(e,t,:effect)
        assert c.identity.authentication_completed_at===now-45
        assert F.scalar("SELECT count(*) FROM driver_fixture.effects")==1
      end},
      {"original completion future30 exact upper window is inclusive", fn ->
        {e,t}=F.seed();now=early_second();e=%{e|authentication_completed_at: now+30}
        assert {:ok,c}=Coordinator.run(e,t,:effect)
        assert c.identity.authentication_completed_at===now+30
      end},
      {"original completion age46 rejects before callback", fn ->
        {e,t}=F.seed();now=early_second();reject(fn -> Coordinator.run(%{e|authentication_completed_at: now-46},t,:effect) end)
      end},
      {"original completion future31 rejects before callback", fn ->
        {e,t}=F.seed();now=early_second();reject(fn -> Coordinator.run(%{e|authentication_completed_at: now+31},t,:effect) end)
      end},
      {"UTF8 credential exact byte length256 accepted and257 rejected", fn ->
        ref=String.duplicate("é",128);{e,t}=F.seed("developer",ref: ref)
        assert byte_size(ref)==256; assert {:ok,c}=Coordinator.run(e,t,:effect)
        assert c.identity.credential_sha256===:crypto.hash(:sha256,ref)
        {e,t}=F.seed("developer",ref: ref<>"x"); reject(fn -> Coordinator.run(e,t,:effect) end)
      end},
      {"transport integers reject equal floats before query or callback", fn ->
        {e,t}=F.seed()
        for field <- [:issued_at,:expires_at,:profile_version] do
          changed=%{e|identity: Map.update!(e.identity,field,&(&1/1))}
          reject(fn -> Coordinator.run(changed,t,:effect) end)
        end
        reject(fn -> Coordinator.run(%{e|authentication_completed_at: e.authentication_completed_at/1},t,:effect) end)
      end},
      {"exact integer profileVersion max and expiry max are preserved", fn ->
        {e,t}=F.seed("developer",issued: 0,expires: 9_007_199_254_740_991,revision: 9_223_372_036_854_775_807)
        F.q("UPDATE mixer_authz.identity_trust_profiles SET current_version=2147483647")
        e=%{e|identity: %{e.identity|profile_version: 2_147_483_647}}
        assert {:ok,c}=Coordinator.run(e,t,:effect)
        assert c.identity.profile_version===2_147_483_647
        assert c.identity.expires_at===9_007_199_254_740_991
        assert c.decision.memberships |> hd() |> Map.fetch!(:revision) ===9_223_372_036_854_775_807
      end},
      {"numeric result validator rejects fraction overflow NaN Infinity and floats", fn ->
        for v <- [Decimal.new("1.1"),Decimal.new("9007199254740992"),Decimal.new("-1"),Decimal.new("NaN"),Decimal.new("Infinity"),1.0,nil] do
          try do Transport.integer!(v);flunk("malformed numeric accepted")
          rescue _ in [Rejected,ArgumentError] -> :ok end
        end
        assert Transport.integer!(Decimal.new("9007199254740991"))===9_007_199_254_740_991
      end},
      {"decision decoder rejects malformed UUID order duplicate count and revision", fn ->
        {e,t}=F.seed();assert {:ok,c}=Coordinator.run(e,t); d=c.decision;m=hd(d.memberships)
        scalars=Enum.map(~w(outcome principal_id binding_id family_id decision_at profile_revision principal_revision family_revision organization_revision project_revision)a,&Map.fetch!(d,&1))
        base=scalars++[[m.lifecycle_id],[m.role],[m.revision]]
        mutations=[List.replace_at(base,10,[<<0>>]),List.replace_at(base,12,[0]),List.replace_at(base,12,[1.0]),List.replace_at(base,11,["unknown"]),scalars++[[m.lifecycle_id,m.lifecycle_id],[m.role,m.role],[1,1]],scalars++[[<<1::128>>,<<0::128>>],[m.role,m.role],[1,1]],scalars++[Enum.map(1..65,&<<&1::128>>),List.duplicate(m.role,65),List.duplicate(1,65)],List.delete_at(base,12)]
        for row<-mutations, do: assert_raise(Rejected,fn -> Transport.decision(%{rows: [row],num_rows: 1},c.admission) end)
        assert_raise Rejected,fn -> Transport.decision(%{rows: [base,base],num_rows: 2},c.admission) end
        F.no_effects()
      end},
      {"secret raw credential not in telemetry query or retained exception", fn ->
        marker="review-sensitive-λ\\ref-84fcf061";{e,t}=F.seed("developer",ref: marker)
        assert {:ok,_}=Coordinator.run(e,t)
        F.q("UPDATE mixer_authz.credential_families SET status='revoked',revision=2")
        error=assert_raise Rejected,fn -> Coordinator.run(e,t,:effect) end
        refute String.contains?(inspect(Map.from_struct(error)),marker)
        queries=Agent.get(DriverEvidence,& &1.queries)
        refute String.contains?(Jason.encode!(queries),marker)
        F.observe(:sensitive_ref,%{telemetry_contains_raw: false,retained_exception_contains_raw: false,exception_reason: inspect(error.reason)})
      end},
      {"unsupported callback remains closed and rolls back",fn ->
        {e,t}=F.seed();assert_raise FunctionClauseError,fn -> Coordinator.run(e,t,{:arbitrary,"SELECT 1"}) end
        F.no_effects()
      end}
    ]
  end

  def run do
    F.q("CREATE SCHEMA driver_fixture");F.q("CREATE TABLE driver_fixture.effects(invocation text NOT NULL)");F.q("GRANT USAGE ON SCHEMA driver_fixture TO mixer_hosted_runtime");F.q("GRANT INSERT ON driver_fixture.effects TO mixer_hosted_runtime")
    results=Enum.map(cases(),fn {name,fun}->
      start=System.monotonic_time(:millisecond)
      result=try do fun.();F.cleaned();%{name: name,passed: true}
      rescue e -> %{name: name,passed: false,error: Exception.format(:error,e,__STACKTRACE__)} end
      result=Map.put(result,:elapsed_ms,System.monotonic_time(:millisecond)-start);IO.puts(Jason.encode!(result));result
    end)
    evidence=Agent.get(DriverEvidence,& &1);out=System.fetch_env!("DRIVER_OUT")
    File.write!(Path.join(out,"driver-tests.json"),Jason.encode!(%{results: results,passed: Enum.count(results,& &1.passed),total: length(results),observations: evidence.observations},pretty: true))
    File.write!(Path.join(out,"driver-queries.json"),Jason.encode!(Enum.reverse(evidence.queries),pretty: true))
    if Enum.any?(results,&(!&1.passed)),do: System.halt(1)
  end
end
