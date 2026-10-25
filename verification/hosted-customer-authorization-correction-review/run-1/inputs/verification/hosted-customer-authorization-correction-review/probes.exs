defmodule MixerHosted.Authorization.IndependentReviewTest do
  use ExUnit.Case, async: false
  alias MixerHosted.Authorization.{Policy, Repository, Scope}
  alias MixerHosted.Identity.VerifiedIdentity

  @now 1_800_000_000
  @project %{organization_id: "org._-A0", project_id: "project._-Z9"}
  @target Map.merge(@project, %{application_id: "app", environment_id: "production"})
  @allowed ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read)

  defp identity do
    %VerifiedIdentity{
      profile_id: "profile", profile_version: 1, issuer: "https://issuer.example.invalid",
      subject: "subject", client_id: "client", credential_ref: "credential",
      issued_at: @now - 10, expires_at: @now + 60, identity_class: :human, scopes: @allowed
    }
  end

  defp member(role \\ "developer", changes \\ %{}) do
    Map.merge(%{id: "membership", principal_id: "principal", role: role, scope: @project,
      project_binding: :exact_project, active: true, not_before: @now - 10,
      expires_at: @now + 60, revision: 1}, changes)
  end

  defp evidence do
    %{binding: %{profile_id: "profile", profile_version: 1,
        issuer: "https://issuer.example.invalid", subject: "subject", client_id: "client",
        identity_class: :human, principal_id: "principal"},
      binding_active: true, profile_active: true,
      principal: %{id: "principal", identity_class: :human, active: true,
        not_before: @now - 10, revision: 1},
      credential: %{reference: "credential", principal_id: "principal", active: true,
        not_before: @now - 10, expires_at: @now + 60, revision: 1},
      target: %{scope: @target, active: true}, memberships: [member()],
      organization_revision: 1, project_revision: 1}
  end

  defp run(e \\ evidence(), i \\ identity(), action \\ "artifact.upload", target \\ @target),
    do: Policy.evaluate(i, action, target, e, @now)

  test "canonical artifact IDs including every allowed byte and 128-byte limits are preserved" do
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
    for id <- [alphabet, String.duplicate("a", 128), ".", "-", "_", "0"] do
      assert MixerHosted.Protocol.ArtifactV3Policy.id?(id)
      assert Scope.identifier?(id)
      assert {:ok, _} = Scope.new(%{@target | organization_id: id})
    end
  end

  test "UTF8 identifiers are byte-bounded and exact without normalization or wildcard expansion" do
    assert {:ok, _} = Scope.new(%{@target | project_id: String.duplicate("é", 64)})
    assert {:error, :invalid_scope} = Scope.new(%{@target | project_id: String.duplicate("é", 65)})
    for bad <- ["*", "\n", "a\t", <<0>>, <<0xFF>>, String.duplicate("a", 129)] do
      assert {:error, :invalid_scope} = Scope.new(%{@target | project_id: bad})
    end
    # A printable '*' within an identifier is literal data, not an all-project grant.
    assert Scope.identifier?("project-*")
    e = %{evidence() | memberships: [member("owner", %{scope: %{@project | project_id: "project-*"}})]}
    assert run(e) == {:error, :not_found}
    assert run(put_in(evidence(), [:target, :scope, :project_id], "é")) == {:error, :not_found}
  end

  test "action target lineage has all ancestors and server scope equality" do
    assert {:ok, _} = run()
    for field <- [:organization_id, :project_id, :application_id, :environment_id] do
      assert run(put_in(evidence(), [:target, :scope, field], "wrong")) == {:error, :not_found}
      assert run(evidence(), identity(), "artifact.upload", Map.delete(@target, field)) ==
        {:error, :invalid_request}
    end
    assert run(put_in(evidence(), [:target, :active], false)) == {:error, :not_found}
    assert {:ok, _} = run(put_in(evidence(), [:target, :scope], @project), identity(), "audit.read", @project)
    assert run(evidence(), identity(), "audit.read") == {:error, :invalid_request}
  end

  test "all six canonical roles retain the selected ceiling and no aliases grant" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        action <- ~w(artifact.read artifact.upload audit.read) do
      target = if action == "audit.read", do: @project, else: @target
      e = %{evidence() | memberships: [member(role)], target: %{scope: target, active: true}}
      allowed = role in ~w(owner administrator developer) or
        (role in ~w(release_manager viewer) and action != "artifact.upload")
      result = run(e, identity(), action, target)
      if allowed, do: assert(match?({:ok, _}, result)), else: assert(result == {:error, :permission_denied})
    end
    for role <- ["release manager", "billing manager", "Owner", "publisher", :owner] do
      assert run(%{evidence() | memberships: [member(role)]}) == {:error, :authorization_unavailable}
    end
  end

  test "eligible memberships union only current roles within an explicit project binding" do
    e = %{evidence() | memberships: [member("viewer", %{id: "viewer"}),
      member("developer", %{id: "disabled", active: false}),
      member("developer", %{id: "future", not_before: @now + 1}),
      member("owner", %{id: "expired", expires_at: @now})]}
    assert run(e) == {:error, :permission_denied}
    assert {:ok, d} = run(e, identity(), "artifact.read")
    assert d.membership_ids == ["viewer"]
    assert d.roles == ["viewer"]
    org = Map.take(@project, [:organization_id])
    for binding <- [:organization_only, :all_projects] do
      e = %{evidence() | memberships: [member("owner", %{scope: org, project_binding: binding})]}
      if binding == :all_projects, do: assert(match?({:ok, _}, run(e))),
        else: assert(run(e) == {:error, :not_found})
    end
    for scope <- [%{@project | organization_id: "other"}, %{@project | project_id: "other"}] do
      assert run(%{evidence() | memberships: [member("owner", %{scope: scope})]}) == {:error, :not_found}
    end
  end

  test "empty and inactive membership sets never become visible through token scopes" do
    for memberships <- [[], [member("owner", %{active: false})]] do
      assert run(%{evidence() | memberships: memberships}) == {:error, :not_found}
    end
    for scopes <- [[], ["owner"], ["project:*"], ["mixer.artifact.*"], ["mixer.artifact.upload "]] do
      assert run(evidence(), %{identity() | scopes: scopes}) == {:error, :permission_denied}
    end
    assert run(%{evidence() | memberships: [member("billing_manager")]}) == {:error, :permission_denied}
  end

  test "all identity profile client subject class and credential bindings are exact" do
    for {field, value} <- [profile_id: "other", profile_version: 2, issuer: "https://other.invalid",
      subject: "other", client_id: "other", identity_class: :service, principal_id: "other"] do
      assert run(put_in(evidence(), [:binding, field], value)) == {:error, :unauthenticated}
    end
    for {field, value} <- [reference: "other", principal_id: "other"] do
      assert run(put_in(evidence(), [:credential, field], value)) == {:error, :unauthenticated}
    end
    for path <- [[:profile_active], [:binding_active], [:principal, :active], [:credential, :active]] do
      assert run(put_in(evidence(), path, false)) == {:error, :unauthenticated}
    end
    assert run(put_in(evidence(), [:principal, :identity_class], :service)) == {:error, :unauthenticated}
  end

  test "expiry and valid-after boundaries do not add a membership or revocation grace" do
    assert {:ok, _} = run()
    for path <- [[:principal, :not_before], [:credential, :not_before]] do
      assert run(put_in(evidence(), path, @now - 9)) == {:error, :unauthenticated}
      assert run(put_in(evidence(), path, @now + 1)) == {:error, :unauthenticated}
      assert {:ok, _} = run(put_in(evidence(), path, @now), %{identity() | issued_at: @now})
    end
    assert run(evidence(), %{identity() | expires_at: @now}) == {:error, :unauthenticated}
    assert run(put_in(evidence(), [:credential, :expires_at], @now)) == {:error, :unauthenticated}
    assert run(evidence(), %{identity() | issued_at: @now + 31}) == {:error, :unauthenticated}
    assert {:ok, _} = run(evidence(), %{identity() | issued_at: @now + 30})
    assert {:ok, _} = run(put_in(evidence(), [:credential, :expires_at], nil))
  end

  test "service CI unknown actions and request header-shaped data have no authority" do
    for klass <- [:service, :ci, "human", nil] do
      assert {:error, _} = run(evidence(), %{identity() | identity_class: klass})
    end
    for action <- ["release.publish", "build.create", "billing.read", "member.manage", "approval.create", "artifact.read\n", :artifact_read] do
      assert run(evidence(), identity(), action) == {:error, :permission_denied}
    end
    for key <- [:role, :roles, :is_admin, :"X-Actor", :"X-Mixer-Role"] do
      assert run(evidence(), Map.put(identity(), key, "owner")) == {:error, :unauthenticated}
      assert run(Map.put(evidence(), key, "owner")) == {:error, :authorization_unavailable}
    end
  end

  test "malformed nested evidence and duplicate memberships fail before eligibility" do
    for key <- [:binding, :principal, :credential, :target, :memberships] do
      for value <- [nil, :unknown, %URI{}, [1 | :tail]] do
        assert run(Map.put(evidence(), key, value)) == {:error, :authorization_unavailable}
      end
    end
    for item <- [Map.put(member(), :unknown, true), Map.delete(member(), :role),
      member("owner", %{project_binding: :all_projects}), member("owner", %{scope: @target}),
      member("owner", %{principal_id: "other"})] do
      assert run(%{evidence() | memberships: [item]}) == {:error, :authorization_unavailable}
    end
    assert run(%{evidence() | memberships: [member(), member("owner", %{active: false})]}) ==
      {:error, :authorization_unavailable}
  end

  test "membership and scope lists enforce finite limits before traversal" do
    members = for n <- 1..64, do: member("developer", %{id: "m-#{n}"})
    assert {:ok, _} = run(%{evidence() | memberships: members})
    for list <- [members ++ [member()], [member() | :improper], List.duplicate(member(), 100_000)] do
      assert run(%{evidence() | memberships: list}) == {:error, :authorization_unavailable}
    end
    scopes = ["mixer.artifact.upload" | (for n <- 1..31, do: "unknown-#{n}")]
    assert {:ok, _} = run(evidence(), %{identity() | scopes: scopes})
    for list <- [scopes ++ ["one-too-many"], ["mixer.artifact.upload" | :improper], ["x", "x"],
      [String.duplicate("é", 129)], [<<0xFF>>]] do
      assert run(evidence(), %{identity() | scopes: list}) == {:error, :unauthenticated}
    end
  end

  test "closed structs maps and numeric metadata reject impossible shapes without throwing" do
    for bad <- [nil, true, 0, -1, 9_007_199_254_740_992, 1.0] do
      for path <- [[:principal, :revision], [:credential, :revision], [:organization_revision], [:project_revision]] do
        assert run(put_in(evidence(), path, bad)) == {:error, :authorization_unavailable}
      end
    end
    for bad <- [nil, true, -1, 9_007_199_254_740_992, 1.0] do
      assert Policy.evaluate(identity(), "artifact.upload", @target, evidence(), bad) == {:error, :invalid_request}
    end
    for bad <- [Map.from_struct(identity()), Map.delete(identity(), :client_id),
      Map.put(identity(), :unknown, true), %{identity() | profile_version: 2_147_483_648}] do
      assert run(evidence(), bad) == {:error, :unauthenticated}
    end
    assert Scope.new(Map.put(struct!(Scope, @target), :unknown, true)) == {:error, :invalid_scope}
  end

  defmodule FixtureRepository do
    def with_evidence(lookup, callback) do
      send(self(), {:lookup, lookup})
      callback.(Process.get(:review_evidence))
    end
  end

  defmodule BadRepository do
    def with_evidence(_, _), do: Process.get(:review_bad_result)
  end

  defmodule RaisingRepository do
    def with_evidence(_, _), do: raise("synthetic secret must not escape")
  end

  defmodule ThrowingRepository do
    def with_evidence(_, _), do: throw({:synthetic_secret, "redacted"})
  end

  defmodule ExitingRepository do
    def with_evidence(_, _), do: exit({:synthetic_secret, "redacted"})
  end

  test "repository defaults unavailable and handles known malformed results raises throws and exits" do
    assert Repository.evaluate(identity(), "artifact.upload", @target, @now) == {:error, :authorization_unavailable}
    for module <- [RaisingRepository, ThrowingRepository, ExitingRepository, "http-input", __MODULE__, nil] do
      assert Repository.evaluate(identity(), "artifact.upload", @target, @now, module) == {:error, :authorization_unavailable}
    end
    for result <- [nil, :ok, {:ok, %{}}, {:error, :secret}, {:error, :unauthenticated, "secret"}] do
      Process.put(:review_bad_result, result)
      assert Repository.evaluate(identity(), "artifact.upload", @target, @now, BadRepository) == {:error, :authorization_unavailable}
    end
  end

  test "repository lookup omits roles scopes and bearer and invalid requests do not invoke it" do
    Process.put(:review_evidence, evidence())
    assert {:ok, _} = Repository.evaluate(identity(), "artifact.upload", @target, @now, FixtureRepository)
    assert_received {:lookup, lookup}
    assert Enum.sort(Map.keys(lookup.identity)) == Enum.sort([:profile_id, :profile_version, :issuer,
      :subject, :client_id, :identity_class, :credential_ref])
    for {i, action, target} <- [{nil, "artifact.upload", @target}, {identity(), "release.publish", @target},
      {identity(), "artifact.upload", @project}, {%{identity() | identity_class: :service}, "artifact.upload", @target}] do
      assert {:error, _} = Repository.evaluate(i, action, target, @now, FixtureRepository)
      refute_received {:lookup, _}
    end
  end

  test "old supplied evidence remains an explicit stale snapshot limitation" do
    old = evidence()
    assert {:ok, _} = run(old)
    revoked = put_in(old, [:credential, :active], false)
    assert run(revoked) == {:error, :unauthenticated}
    assert {:ok, _} = run(old)
  end

  @tag :malformed_decision_observation
  test "malformed Decision returned by a configured repository is sanitized" do
    {:ok, scope} = Scope.new(@target)
    malformed = struct(Policy.Decision, action: "artifact.upload", target: scope)
    Process.put(:review_bad_result, {:ok, malformed})
    assert Repository.evaluate(identity(), "artifact.upload", @target, @now, BadRepository) ==
      {:error, :authorization_unavailable}
  end

  defmodule CallbackResultRepository do
    def with_evidence(_lookup, callback) do
      result = callback.(Process.get(:review_evidence))
      Process.get(:review_transform, fn value -> value end).(result)
    end
  end

  defp through_callback(transform \\ fn value -> value end, e \\ evidence(),
      i \\ identity(), action \\ "artifact.upload", target \\ @target) do
    Process.put(:review_evidence, e)
    Process.put(:review_transform, transform)
    Repository.evaluate(i, action, target, @now, CallbackResultRepository)
  end

  test "corrected repository preserves all supported role outcomes and multi-role projections" do
    for role <- ~w(owner administrator developer release_manager billing_manager viewer),
        action <- ~w(artifact.read artifact.upload audit.read) do
      target = if action == "audit.read", do: @project, else: @target
      e = %{evidence() | memberships: [member(role)], target: %{scope: target, active: true}}
      assert through_callback(& &1, e, identity(), action, target) == run(e, identity(), action, target)
    end
    members = for n <- 1..64, do: member("owner", %{id: "m-#{n}"})
    e = %{evidence() | memberships: members}
    assert {:ok, decision} = through_callback(& &1, e)
    assert length(decision.membership_ids) == 64
    e = %{evidence() | memberships: [member("owner", %{id: "owner"}),
      member("administrator", %{id: "admin"}), member("developer", %{id: "dev"})]}
    assert {:ok, decision} = through_callback(& &1, e)
    assert decision.roles == ["administrator", "developer", "owner"]
  end

  test "complete unwrapped success without callback cannot bypass the current envelope" do
    assert {:ok, decision} = run()
    Process.put(:review_bad_result, {:ok, decision})
    assert Repository.evaluate(identity(), "artifact.upload", @target, @now, BadRepository) ==
      {:error, :authorization_unavailable}
    for marker <- [make_ref(), nil, false, 1, "reference", :reference] do
      Process.put(:review_bad_result, {:policy_evaluation, marker, {:ok, decision}})
      assert Repository.evaluate(identity(), "artifact.upload", @target, @now, BadRepository) ==
        {:error, :authorization_unavailable}
    end
  end

  test "missing altered and cross-request envelopes fail including legitimate old successes" do
    transforms = [
      fn {:policy_evaluation, _, result} -> result end,
      fn {:policy_evaluation, _, result} -> {:policy_evaluation, make_ref(), result} end,
      fn {:policy_evaluation, _, result} -> {:policy_evaluation, nil, result} end,
      fn {:policy_evaluation, ref, result} -> {:wrong_tag, ref, result} end,
      fn {:policy_evaluation, ref, result} -> {:policy_evaluation, ref, result, :extra} end
    ]
    for transform <- transforms do
      assert through_callback(transform) == {:error, :authorization_unavailable}
    end
    assert {:ok, _} = through_callback(fn value -> Process.put(:old_review_envelope, value); value end)
    assert through_callback(fn _ -> Process.get(:old_review_envelope) end) ==
      {:error, :authorization_unavailable}
  end

  test "callback projection validates every closed field and rejects partial struct maps" do
    assert {:ok, original} = run()
    for key <- Map.keys(Map.from_struct(original)) do
      assert through_callback(fn {:policy_evaluation, ref, {:ok, d}} ->
        {:policy_evaluation, ref, {:ok, Map.delete(d, key)}} end) ==
        {:error, :authorization_unavailable}, inspect(key)
      assert through_callback(fn {:policy_evaluation, ref, {:ok, d}} ->
        {:policy_evaluation, ref, {:ok, Map.put(d, key, nil)}} end) ==
        {:error, :authorization_unavailable}, inspect(key)
    end
    for change <- [fn d -> Map.from_struct(d) end, fn d -> Map.put(d, :role, "owner") end,
      fn _ -> struct(Policy.Decision, action: "artifact.upload", target: struct!(Scope, @target)) end] do
      assert through_callback(fn {:policy_evaluation, ref, {:ok, d}} ->
        {:policy_evaluation, ref, {:ok, change.(d)}} end) == {:error, :authorization_unavailable}
    end
  end

  test "callback projection is request-bound and uses existing finite bounds" do
    changes = [action: "artifact.read", target: struct!(Scope, %{@target | environment_id: "other"}),
      credential_ref: "other", profile_id: "other", profile_version: 2, evaluated_at: @now - 1,
      principal_id: String.duplicate("p", 129), principal_id: <<0xFF>>,
      membership_ids: [], membership_ids: ["x" | :tail], membership_ids: ["same", "same"],
      membership_ids: ["z", "a"], membership_ids: Enum.map(1..65, &"m-#{&1}"),
      roles: [], roles: ["viewer"], roles: ["owner", "owner"], roles: ["owner" | :tail],
      roles: ["administrator", "developer"],
      principal_revision: 0, credential_revision: false, organization_revision: 1.0,
      project_revision: 9_007_199_254_740_992]
    for {key, value} <- changes do
      assert through_callback(fn {:policy_evaluation, ref, {:ok, d}} ->
        {:policy_evaluation, ref, {:ok, Map.put(d, key, value)}} end) ==
        {:error, :authorization_unavailable}, inspect({key, value})
    end
    assert {:ok, _} = through_callback(fn {:policy_evaluation, ref, {:ok, d}} ->
      {:policy_evaluation, ref, {:ok, %{d | principal_revision: 9_007_199_254_740_991,
        credential_revision: 9_007_199_254_740_991, organization_revision: 9_007_199_254_740_991,
        project_revision: 9_007_199_254_740_991}}} end)
  end

  test "unchanged callback errors and exception boundaries remain bounded" do
    for error <- [:invalid_request, :unauthenticated, :not_found, :permission_denied, :authorization_unavailable] do
      assert through_callback(fn {:policy_evaluation, ref, _} ->
        {:policy_evaluation, ref, {:error, error}} end) == {:error, error}
      Process.put(:review_bad_result, {:error, error})
      assert Repository.evaluate(identity(), "artifact.upload", @target, @now, BadRepository) == {:error, error}
    end
    for result <- [{:error, "secret"}, {:ok, nil}, nil, :ok, {:error, :unauthenticated, "secret"}] do
      assert through_callback(fn {:policy_evaluation, ref, _} ->
        {:policy_evaluation, ref, result} end) == {:error, :authorization_unavailable}
    end
    assert through_callback(fn _ -> raise("synthetic secret") end) == {:error, :authorization_unavailable}
    assert through_callback(fn _ -> throw(:synthetic_secret) end) == {:error, :authorization_unavailable}
    assert through_callback(fn _ -> exit(:synthetic_secret) end) == {:error, :authorization_unavailable}
  end

  test "new envelope still does not establish freshness of supplied evidence" do
    old = evidence()
    assert {:ok, _} = through_callback(& &1, old)
    assert through_callback(& &1, put_in(old, [:credential, :active], false)) == {:error, :unauthenticated}
    # A fresh invocation/reference over an old snapshot still evaluates. Durable
    # current-state lookup and locking remain the future adapter's obligation.
    assert {:ok, _} = through_callback(& &1, old)
  end
end
