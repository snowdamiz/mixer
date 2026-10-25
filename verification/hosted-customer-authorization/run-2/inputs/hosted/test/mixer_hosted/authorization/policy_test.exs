defmodule MixerHosted.Authorization.PolicyTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Authorization.{Policy, Repository, Scope}
  alias MixerHosted.Identity.VerifiedIdentity

  @now 1_800_000_000
  @scope %{
    organization_id: "organization-a",
    project_id: "project-a",
    application_id: "application-a",
    environment_id: "environment-a"
  }
  @project Map.take(@scope, [:organization_id, :project_id])
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @actions ~w(artifact.read artifact.upload audit.read)

  def identity(changes \\ %{}) do
    struct!(
      VerifiedIdentity,
      Map.merge(
        %{
          profile_id: "synthetic-profile",
          profile_version: 7,
          issuer: "https://identity.example.invalid",
          subject: "synthetic-subject",
          client_id: "synthetic-client",
          credential_ref: "synthetic-credential",
          issued_at: @now - 10,
          expires_at: @now + 100,
          identity_class: :human,
          scopes: ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read)
        },
        changes
      )
    )
  end

  def member(role \\ "developer", changes \\ %{}) do
    Map.merge(
      %{
        id: "membership-#{role}",
        principal_id: "principal-a",
        role: role,
        scope: @project,
        project_binding: :exact_project,
        active: true,
        not_before: @now - 20,
        expires_at: @now + 200,
        revision: 3
      },
      changes
    )
  end

  def evidence(role \\ "developer", target \\ @scope) do
    %{
      binding: %{
        profile_id: "synthetic-profile",
        profile_version: 7,
        issuer: "https://identity.example.invalid",
        subject: "synthetic-subject",
        client_id: "synthetic-client",
        identity_class: :human,
        principal_id: "principal-a"
      },
      binding_active: true,
      profile_active: true,
      principal: %{
        id: "principal-a",
        identity_class: :human,
        active: true,
        not_before: @now - 20,
        revision: 11
      },
      credential: %{
        reference: "synthetic-credential",
        principal_id: "principal-a",
        active: true,
        not_before: @now - 20,
        expires_at: @now + 200,
        revision: 13
      },
      target: %{scope: target, active: true},
      memberships: [member(role)],
      organization_revision: 17,
      project_revision: 19
    }
  end

  defp target("audit.read"), do: @project
  defp target(_), do: @scope

  defp evaluate(evidence, action \\ "artifact.upload", identity \\ identity(), now \\ @now),
    do: Policy.evaluate(identity, action, target(action), evidence, now)

  test "the six-role matrix intersects the exact supported token scope" do
    for role <- @roles, action <- @actions do
      allowed =
        role in ~w(owner administrator developer) or
          (role in ~w(release_manager viewer) and action != "artifact.upload")

      result = evaluate(evidence(role, target(action)), action)

      if allowed do
        assert {:ok, decision} = result
        assert decision.roles == [role]
        assert decision.membership_ids == ["membership-#{role}"]
      else
        assert result == {:error, :permission_denied}
      end

      assert evaluate(evidence(role, target(action)), action, identity(%{scopes: []})) ==
               {:error, :permission_denied}
    end
  end

  test "a decision is a sorted audit projection of only applicable eligible grants" do
    grants = [
      member("viewer"),
      member("owner", %{id: "a-owner"}),
      member("owner", %{id: "b-owner"}),
      member("developer", %{id: "revoked", active: false}),
      member("administrator", %{id: "other-project", scope: %{@project | project_id: "other"}})
    ]

    assert {:ok, decision} = evaluate(%{evidence() | memberships: grants}, "artifact.read")
    assert decision.roles == ["owner", "viewer"]
    assert decision.membership_ids == ["a-owner", "b-owner", "membership-viewer"]
    assert decision.principal_id == "principal-a"
    assert decision.principal_revision == 11
    assert decision.credential_revision == 13
    assert decision.organization_revision == 17
    assert decision.project_revision == 19
    assert decision.evaluated_at == @now
    refute Map.has_key?(decision, :token)
    refute Map.has_key?(decision, :authorized_context)
  end

  test "a scope or arbitrary token scope cannot create membership" do
    for scopes <- [[], ["owner"], ["project:*"], ["mixer.artifact.upload"]] do
      assert evaluate(
               %{evidence() | memberships: []},
               "artifact.upload",
               identity(%{scopes: scopes})
             ) ==
               {:error, :not_found}
    end
  end

  test "each artifact tenant ancestor must equal the server-loaded actual target" do
    for field <- Map.keys(@scope) do
      wrong = put_in(evidence(), [:target, :scope, field], "different")
      assert evaluate(wrong) == {:error, :not_found}
    end

    assert evaluate(put_in(evidence(), [:target, :active], false)) == {:error, :not_found}
  end

  test "a membership for another tenant or project grants no visibility" do
    for field <- [:organization_id, :project_id] do
      wrong =
        put_in(evidence(), [:memberships], [
          member("owner", %{scope: Map.put(@project, field, "different")})
        ])

      assert evaluate(wrong) == {:error, :not_found}
    end
  end

  test "organization-only membership does not imply project visibility" do
    scope = Map.take(@scope, [:organization_id])
    organization_only = member("owner", %{scope: scope, project_binding: :organization_only})
    assert evaluate(%{evidence() | memberships: [organization_only]}) == {:error, :not_found}

    explicit = %{organization_only | project_binding: :all_projects}
    assert {:ok, _} = evaluate(%{evidence() | memberships: [explicit]})
    wrong_tenant = put_in(explicit, [:scope, :organization_id], "other")
    assert evaluate(%{evidence() | memberships: [wrong_tenant]}) == {:error, :not_found}
  end

  test "revoked, future and expired memberships cannot contribute a role" do
    for changes <- [%{active: false}, %{not_before: @now + 1}, %{expires_at: @now}] do
      assert evaluate(%{evidence() | memberships: [member("owner", changes)]}) ==
               {:error, :not_found}
    end

    assert {:ok, _} =
             evaluate(%{
               evidence()
               | memberships: [member("owner", %{not_before: @now, expires_at: nil})]
             })
  end

  test "every identity binding field is matched exactly" do
    for {field, wrong} <- [
          profile_id: "different",
          profile_version: 8,
          issuer: "https://other.invalid",
          subject: "different",
          client_id: "different",
          identity_class: :service,
          principal_id: "different"
        ] do
      assert evaluate(put_in(evidence(), [:binding, field], wrong)) == {:error, :unauthenticated}
    end
  end

  test "current profile, binding, principal and credential revocation denies" do
    for path <- [
          [:profile_active],
          [:binding_active],
          [:principal, :active],
          [:credential, :active]
        ] do
      assert evaluate(put_in(evidence(), path, false)) == {:error, :unauthenticated}
    end
  end

  test "credential must be bound to this exact principal and verified reference" do
    for {field, wrong} <- [reference: "other", principal_id: "other"] do
      assert evaluate(put_in(evidence(), [:credential, field], wrong)) ==
               {:error, :unauthenticated}
    end

    assert evaluate(put_in(evidence(), [:principal, :identity_class], :service)) ==
             {:error, :unauthenticated}
  end

  test "current principal and credential valid-after fence older tokens" do
    for path <- [[:principal, :not_before], [:credential, :not_before]] do
      assert evaluate(put_in(evidence(), path, @now - 9)) == {:error, :unauthenticated}
    end

    assert evaluate(
             put_in(evidence(), [:principal, :not_before], @now + 1),
             "artifact.upload",
             identity(%{issued_at: @now + 1})
           ) == {:error, :unauthenticated}

    assert evaluate(put_in(evidence(), [:credential, :expires_at], @now)) ==
             {:error, :unauthenticated}
  end

  test "verified token expiry and existing issued-at skew remain exclusive and bounded" do
    assert evaluate(evidence(), "artifact.upload", identity(%{expires_at: @now})) ==
             {:error, :unauthenticated}

    assert evaluate(evidence(), "artifact.upload", identity(%{issued_at: @now + 31})) ==
             {:error, :unauthenticated}

    assert {:ok, _} = evaluate(evidence(), "artifact.upload", identity(%{issued_at: @now + 30}))
  end

  test "service and CI cannot become human owners or gain these pending operations" do
    service = identity(%{identity_class: :service})

    for role <- @roles, action <- @actions do
      assert evaluate(evidence(role, target(action)), action, service) ==
               {:error, :permission_denied}
    end
  end

  test "build, billing, release, approval and member operations all fail closed" do
    for action <-
          ~w(build.read build.create build.cancel billing.read billing.manage usage.read
      release.validate release.publish release.promote release.rollback release.halt approval.create
      member.manage organization.transfer project.create source.read logs.read symbols.read source_map.read),
        role <- @roles do
      assert Policy.evaluate(identity(), action, @scope, evidence(role), @now) ==
               {:error, :permission_denied}
    end
  end

  test "wrong action-specific target shapes reject before a repository lookup" do
    for scope <- [
          Map.take(@scope, [:organization_id]),
          @project,
          Map.drop(@scope, [:environment_id])
        ] do
      assert Policy.evaluate(identity(), "artifact.read", scope, evidence(), @now) ==
               {:error, :invalid_request}
    end

    assert Policy.evaluate(identity(), "audit.read", @scope, evidence(), @now) ==
             {:error, :invalid_request}
  end

  test "malformed, unknown and duplicate membership evidence fails unavailable" do
    for grants <- [
          [member("publisher")],
          [member("owner", %{role: "Owner"})],
          [member(), member()],
          [Map.put(member(), :is_admin, true)],
          [Map.delete(member(), :revision)],
          [member("owner", %{principal_id: "other"})],
          [member("owner", %{project_binding: :all_projects})],
          [member("owner", %{scope: @scope})]
        ] do
      assert evaluate(%{evidence() | memberships: grants}) == {:error, :authorization_unavailable}
    end
  end

  test "lists are bounded before traversal and improper lists reject" do
    max = for n <- 1..64, do: member("viewer", %{id: "member-#{n}"})
    assert {:ok, _} = evaluate(%{evidence() | memberships: max}, "artifact.read")

    for grants <- [max ++ [member()], [member() | :improper], :not_a_list] do
      assert evaluate(%{evidence() | memberships: grants}) == {:error, :authorization_unavailable}
    end

    for scopes <- [
          List.duplicate("scope", 33),
          ["scope" | :improper],
          ["scope", "scope"],
          [42],
          [String.duplicate("s", 257)]
        ] do
      assert evaluate(evidence(), "artifact.upload", identity(%{scopes: scopes})) ==
               {:error, :unauthenticated}
    end
  end

  test "evidence has a closed bounded shape at every record level" do
    for path <- [[], [:binding], [:principal], [:credential], [:target]] do
      changed =
        if path == [],
          do: Map.put(evidence(), :raw_token, "redacted"),
          else: update_in(evidence(), path, &Map.put(&1, :unknown, true))

      assert evaluate(changed) == {:error, :authorization_unavailable}
    end

    for value <- [nil, [], %{}, %URI{}, Map.delete(evidence(), :memberships)] do
      assert evaluate(value) == {:error, :authorization_unavailable}
    end
  end

  test "revision and temporal metadata do not accept impossible ranges or booleans" do
    for bad <- [nil, 0, -1, true, 9_007_199_254_740_992] do
      for path <- [
            [:organization_revision],
            [:project_revision],
            [:principal, :revision],
            [:credential, :revision],
            [:binding, :profile_version]
          ] do
        assert evaluate(put_in(evidence(), path, bad)) == {:error, :authorization_unavailable}
      end
    end

    for bad <- [nil, -1, true, 9_007_199_254_740_992] do
      assert evaluate(evidence(), "artifact.upload", identity(), bad) ==
               {:error, :invalid_request}
    end
  end

  test "malformed identity is never treated as a verified caller" do
    for value <- [
          nil,
          Map.from_struct(identity()),
          %URI{},
          %{identity() | profile_version: 0},
          Map.put(identity(), :role, "owner"),
          %{identity() | expires_at: @now - 20},
          %{identity() | subject: String.duplicate("s", 257)},
          %{identity() | issued_at: false}
        ] do
      assert Policy.evaluate(value, "artifact.upload", @scope, evidence(), @now) ==
               {:error, :unauthenticated}
    end
  end

  test "stale supplied values cannot claim to prove a durable revocation check" do
    old = evidence()
    assert {:ok, _} = evaluate(old)
    assert evaluate(put_in(old, [:principal, :active], false)) == {:error, :unauthenticated}
    # This deliberate control demonstrates the pure boundary: retained old data
    # still evaluates. Only a fresh real transaction can make revocation durable.
    assert {:ok, _} = evaluate(old)
  end

  test "scope parsing rejects ancestor gaps, wildcards, foreign keys and oversized identifiers" do
    for value <- [
          nil,
          %{},
          Map.drop(@scope, [:organization_id]),
          Map.drop(@scope, [:project_id]),
          Map.drop(@scope, [:application_id]),
          Map.put(@scope, :platform, :ios),
          %{@scope | project_id: "*"},
          %{@scope | organization_id: "bad\nline"},
          %{@scope | project_id: <<255>>},
          %{@scope | environment_id: String.duplicate("e", 129)},
          Map.put(struct!(Scope, @scope), :extra, true)
        ] do
      assert Scope.new(value) == {:error, :invalid_scope}
    end

    assert {:ok, scope} = Scope.new(@scope)
    assert Scope.new(scope) == {:ok, scope}
    assert {:ok, _} = Scope.new(%{@scope | environment_id: String.duplicate("e", 128)})
  end

  defmodule SyntheticRepository do
    @behaviour Repository
    def with_evidence(lookup, callback) do
      send(self(), {:authorization_lookup, lookup})
      callback.(Process.get(:authorization_fixture))
    end
  end

  defmodule BrokenRepository do
    @behaviour Repository
    def with_evidence(_lookup, _callback),
      do: raise("synthetic credential details must not escape")
  end

  defmodule MalformedRepository do
    @behaviour Repository
    def with_evidence(_lookup, _callback), do: {:ok, %{role: "owner"}}
  end

  test "repository defaults unavailable, rejects invalid dependencies and sanitizes failures" do
    assert Repository.evaluate(identity(), "artifact.upload", @scope, @now) ==
             {:error, :authorization_unavailable}

    for repository <- [nil, "from-http", __MODULE__, BrokenRepository, MalformedRepository] do
      assert Repository.evaluate(identity(), "artifact.upload", @scope, @now, repository) ==
               {:error, :authorization_unavailable}
    end
  end

  test "repository lookup is exact and never includes raw bearer, role or token scopes" do
    Process.put(:authorization_fixture, evidence())

    assert {:ok, _} =
             Repository.evaluate(identity(), "artifact.upload", @scope, @now, SyntheticRepository)

    assert_received {:authorization_lookup, lookup}
    assert lookup.action == "artifact.upload"
    assert lookup.target.organization_id == "organization-a"

    assert lookup.identity == %{
             profile_id: "synthetic-profile",
             profile_version: 7,
             issuer: "https://identity.example.invalid",
             subject: "synthetic-subject",
             client_id: "synthetic-client",
             credential_ref: "synthetic-credential",
             identity_class: :human
           }
  end

  test "invalid requests cannot trigger a policy repository callback" do
    for {caller, action, scope} <- [
          {nil, "artifact.read", @scope},
          {identity(), "release.publish", @scope},
          {identity(), "artifact.upload", @project},
          {identity(%{identity_class: :service}), "artifact.read", @scope}
        ] do
      assert {:error, _} = Repository.evaluate(caller, action, scope, @now, SyntheticRepository)
      refute_received {:authorization_lookup, _}
    end
  end

  test "a second repository call observes changed synthetic current state" do
    Process.put(:authorization_fixture, evidence())

    assert {:ok, _} =
             Repository.evaluate(identity(), "artifact.upload", @scope, @now, SyntheticRepository)

    Process.put(:authorization_fixture, put_in(evidence(), [:credential, :active], false))

    assert Repository.evaluate(identity(), "artifact.upload", @scope, @now, SyntheticRepository) ==
             {:error, :unauthenticated}

    # A fixture callback is not a database, RLS or race-acceptance receipt.
  end
end
