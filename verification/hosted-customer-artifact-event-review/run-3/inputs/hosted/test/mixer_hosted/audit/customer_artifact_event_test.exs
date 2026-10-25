defmodule MixerHosted.Audit.CustomerArtifactEventIdentityProbe do
  def credential_ref, do: notify("credential")
  def profile_id, do: notify("profile")
  def profile_version, do: notify(1)

  defp notify(value) do
    send(self(), :invalid_identity_callback)
    value
  end
end

defmodule MixerHosted.Audit.CustomerArtifactEventTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Audit.CustomerArtifactEvent, as: Event
  alias MixerHosted.Audit.CustomerArtifactEvent.Record
  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Transaction.Snapshot
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactCBOR

  @max 9_007_199_254_740_991
  @packet Path.expand("../../../../verification/hosted-customer-artifact-event", __DIR__)
  @fields ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)
  @error {:error, :invalid_audit_event}

  def fixture do
    identity = %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://issuer.example/é",
      subject: "用户:raw",
      client_id: "client:ä",
      credential_ref: "credential:ß",
      issued_at: 80,
      expires_at: 1000,
      identity_class: :human,
      scopes: ["mixer.artifact.upload", "unrecorded-scope"]
    }

    target = %Scope{
      organization_id: "org",
      project_id: "project",
      application_id: "app",
      environment_id: "env"
    }

    member = %{
      id: "member-a",
      principal_id: "person",
      role: "developer",
      scope: %Scope{organization_id: "org", project_id: "project"},
      project_binding: :exact_project,
      active: true,
      not_before: 50,
      expires_at: 900,
      revision: 9
    }

    snapshot = %{
      request_id: "0123456789abcdef0123456789abcdef",
      profile: %{
        id: "profile",
        version: 1,
        issuer: identity.issuer,
        client_id: identity.client_id,
        identity_class: "human",
        active: true,
        state_revision: 2
      },
      binding: %{
        profile_id: "profile",
        profile_version: 1,
        subject_digest: plain_hash(identity.subject),
        identity_class: "human",
        principal_id: "person",
        active: true,
        revision: 3
      },
      principal: %{id: "person", identity_class: :human, active: true, not_before: 0, revision: 4},
      credential: %{
        profile_id: "profile",
        profile_version: 1,
        reference: identity.credential_ref,
        principal_id: "person",
        family_id: "family",
        active: true,
        not_before: 50,
        expires_at: 950,
        revision: 5
      },
      family: %{
        id: "family",
        profile_id: "profile",
        profile_version: 1,
        principal_id: "person",
        active: true,
        not_before: 40,
        expires_at: 960,
        revision: 6
      },
      memberships: [member],
      organization_head: %{organization_id: "org", revision: 7},
      project_head: %{organization_id: "org", project_id: "project", revision: 8},
      identity:
        identity
        |> Map.from_struct()
        |> Map.delete(:subject)
        |> Map.put(:subject_digest, plain_hash(identity.subject)),
      action: "artifact.upload",
      target: target,
      checked_at: 100
    }

    artifact = %{
      organization_id: "org",
      project_id: "project",
      application_id: "app",
      environment_id: "env",
      platform: "ios",
      runtime_sha256: String.duplicate("a", 64),
      manifest_sha256: String.duplicate("b", 64),
      payload_sha256: String.duplicate("c", 64),
      envelope_sha256: String.duplicate("d", 64)
    }

    {:ok, genesis} = Event.genesis("org", "project")

    command = %{
      sequence: 1,
      previous_state_sha256: genesis,
      previous_event_sha256: "",
      outcome: "created",
      reason: "reason é",
      source_ip: "2001:db8::1"
    }

    {identity, snapshot, %{snapshot | checked_at: 102}, artifact, command}
  end

  def build({identity, locked, fresh, artifact, command}),
    do: Event.build(identity, locked, fresh, artifact, command)

  def record do
    {:ok, record} = build(fixture())
    record
  end

  defp plain_hash(value), do: :crypto.hash(:sha256, value) |> Base.encode16(case: :lower)
  defp event_hash(bytes), do: plain_hash("mixer.hosted.customer.audit.v2\0" <> bytes)

  defp sealed(display) do
    {:ok, bytes} = ArtifactCBOR.encode(Enum.map(@fields, &Map.fetch!(display, &1)))
    Map.put(display, "event_sha256", event_hash(bytes))
  end

  defp set(array, index, value), do: List.replace_at(array, index, value)

  defp changed(display, field, index, value),
    do: Map.update!(display, field, &set(&1, index, value))

  test "malformed module identity cannot invoke callbacks before rejection" do
    {identity, locked, fresh, artifact, command} = fixture()

    for invalid <- [
          MixerHosted.Audit.CustomerArtifactEventIdentityProbe,
          Map.from_struct(identity)
        ] do
      assert {:error, :invalid_audit_event} =
               Event.build(invalid, locked, fresh, artifact, command)

      refute_received :invalid_identity_callback
    end
  end

  test "independent canonical array bytes and all domain-separated golden digests" do
    result = record()

    expected =
      @packet
      |> Path.join("golden_event.hex")
      |> File.read!()
      |> String.trim()
      |> Base.decode16!(case: :lower)

    hashes =
      @packet
      |> Path.join("golden_hashes.txt")
      |> File.read!()
      |> String.split("\n", trim: true)
      |> Map.new(fn line -> line |> String.split("=", parts: 2) |> List.to_tuple() end)

    assert result.event_cbor == expected
    assert result.event_sha256 == hashes["event"]
    assert result.display["previous_state_sha256"] == hashes["genesis"]
    assert result.display["current_state_sha256"] == hashes["state"]
    assert result.display["request_sha256"] == hashes["request"]

    for {field, index} <- [
          {"binding", 4},
          {"issuer", 5},
          {"subject", 6},
          {"client", 7},
          {"credential_ref", 8}
        ],
        do: assert(Enum.at(result.display["actor"], index) == hashes[field])

    assert Event.decode(result.display) == {:ok, result}
    assert Event.validate_row(result) == :ok
    assert Event.validate_row(Map.from_struct(result)) == :ok
    assert Event.validate_edge(result, nil) == :ok
  end

  test "raw Unicode references retain separate exact byte namespaces and never leak" do
    {i, _, _, _, _} = fixture()
    result = record()

    for raw <- [i.issuer, i.subject, i.client_id, i.credential_ref, "unrecorded-scope"] do
      refute :binary.match(result.event_cbor, raw) != :nomatch
    end

    refute Enum.at(result.display["actor"], 6) ==
             plain_hash("mixer.hosted.customer.subject.v2\0" <> plain_hash(i.subject))

    actor = result.display["actor"]
    assert length(Enum.uniq(Enum.slice(actor, 4, 5))) == 5
    {i, locked, fresh, artifact, command} = fixture()
    other = %{i | issuer: i.issuer <> "/"}
    assert Event.build(other, locked, fresh, artifact, command) == @error
  end

  test "build accepts changed selected live memberships while requiring immutable locked evidence" do
    {i, l, f, a, c} = fixture()
    member = hd(f.memberships)

    fresh_member = %{
      member
      | id: "member-b",
        not_before: 101,
        expires_at: 103,
        revision: 10,
        role: "owner"
    }

    assert {:ok, result} = Event.build(i, l, %{f | memberships: [fresh_member]}, a, c)

    assert List.last(result.display["authorization"]) == [
             ["member-b", "owner", 10, "org", ["project"], "exact_project", true, 101, [103]]
           ]

    org_member = %{
      member
      | scope: %Scope{organization_id: "org"},
        project_binding: :all_projects,
        expires_at: nil
    }

    assert {:ok, _} =
             Event.build(
               i,
               %{l | memberships: [org_member]},
               %{f | memberships: [org_member]},
               a,
               c
             )

    for field <- [
          :profile,
          :binding,
          :principal,
          :credential,
          :family,
          :organization_head,
          :project_head
        ] do
      nested = Map.fetch!(f, field)
      revision = if field == :profile, do: :state_revision, else: :revision
      changed = Map.update!(nested, revision, &(&1 + 1))
      assert Event.build(i, l, Map.put(f, field, changed), a, c) == @error
    end

    assert Event.build(i, l, %{f | request_id: String.duplicate("f", 32)}, a, c) == @error
  end

  test "both snapshots are closed, bounded and validated using the ordinary Snapshot contract" do
    {i, l, f, a, c} = fixture()

    decision = %Policy.Decision{
      action: f.action,
      target: f.target,
      principal_id: "person",
      credential_ref: i.credential_ref,
      profile_id: i.profile_id,
      profile_version: 1,
      membership_ids: ["member-a"],
      roles: ["developer"],
      principal_revision: 4,
      credential_revision: 5,
      organization_revision: 7,
      project_revision: 8,
      evaluated_at: 102
    }

    assert Snapshot.valid?(f, i, decision)

    for field <- Map.keys(f) do
      assert Event.build(i, l, Map.delete(f, field), a, c) == @error
      assert Event.build(i, Map.delete(l, field), f, a, c) == @error
    end

    assert Event.build(i, l, Map.put(f, :unknown, true), a, c) == @error
    assert Event.build(Map.from_struct(i), l, f, a, c) == @error
    assert Event.build(i, l, %{f | action: "artifact.read"}, a, c) == @error
    assert Event.build(i, l, %{f | memberships: [hd(f.memberships) | :improper]}, a, c) == @error

    for field <- [
          :profile,
          :binding,
          :principal,
          :credential,
          :family,
          :identity,
          :organization_head,
          :project_head
        ] do
      nested = Map.fetch!(f, field)

      for key <- Map.keys(nested) do
        assert Event.build(i, l, Map.put(f, field, Map.delete(nested, key)), a, c) == @error
      end

      assert Event.build(i, l, Map.put(f, field, Map.put(nested, :unknown, 1)), a, c) == @error
    end

    member = hd(f.memberships)

    for key <- Map.keys(member),
        do:
          assert(Event.build(i, l, %{f | memberships: [Map.delete(member, key)]}, a, c) == @error)

    assert Event.build(i, l, %{f | memberships: [Map.put(member, :unknown, 1)]}, a, c) == @error
  end

  test "time fences include exact token expiry, credential/family/member ends and five-second effect bound" do
    {i, l, f, a, c} = fixture()
    assert {:ok, _} = Event.build(i, l, %{f | checked_at: 105}, a, c)

    for now <- [99, 106, -1, @max + 1, 102.0],
        do: assert(Event.build(i, l, %{f | checked_at: now}, a, c) == @error)

    for field <- [:credential, :family] do
      for end_at <- [100, 102] do
        changed_l = put_in(l, [field, :expires_at], end_at)
        changed_f = put_in(f, [field, :expires_at], end_at)
        assert Event.build(i, changed_l, changed_f, a, c) == @error
      end
    end

    assert Event.build(i, l, %{f | memberships: [%{hd(f.memberships) | expires_at: 102}]}, a, c) ==
             @error

    expiring = %{i | expires_at: 102}
    il = put_in(l, [:identity, :expires_at], 102)
    ef = put_in(f, [:identity, :expires_at], 102)
    assert Event.build(expiring, il, ef, a, c) == @error
    future = %{i | issued_at: 131}
    il = put_in(l, [:identity, :issued_at], 131)
    ef = put_in(f, [:identity, :issued_at], 131)
    assert Event.build(future, il, ef, a, c) == @error
  end

  test "artifact and command maps are closed and target equals exact snapshot scope" do
    {i, l, f, a, c} = fixture()
    for key <- Map.keys(a), do: assert(Event.build(i, l, f, Map.delete(a, key), c) == @error)
    for key <- Map.keys(c), do: assert(Event.build(i, l, f, a, Map.delete(c, key)) == @error)
    assert Event.build(i, l, f, Map.put(a, :unknown, 1), c) == @error
    assert Event.build(i, l, f, a, Map.put(c, :request_id, l.request_id)) == @error

    for field <- [:organization_id, :project_id, :application_id, :environment_id],
        do: assert(Event.build(i, l, f, Map.put(a, field, "different"), c) == @error)

    for field <- [:runtime_sha256, :manifest_sha256, :payload_sha256, :envelope_sha256],
        bad <- ["", String.duplicate("A", 64), String.duplicate("a", 63), nil],
        do: assert(Event.build(i, l, f, Map.put(a, field, bad), c) == @error)

    assert Event.build(i, l, f, %{a | platform: "web"}, c) == @error
    assert {:ok, _} = Event.build(i, l, f, %{a | platform: "android"}, c)
  end

  test "canonical trusted IP and optional arrays reject ambiguous spellings" do
    {i, l, f, a, c} = fixture()

    for ip <- [nil, "127.0.0.1", "2001:db8::1", "::1", "0.0.0.0"] do
      assert {:ok, result} = Event.build(i, l, f, a, %{c | source_ip: ip})
      assert result.display["source_ip"] == if(is_nil(ip), do: [], else: [ip])
    end

    for ip <- [
          "127.1",
          "127.000.0.1",
          "2001:0db8::1",
          "2001:DB8::1",
          "fe80::1%en0",
          " 127.0.0.1",
          "256.1.1.1",
          "",
          <<255>>,
          1
        ],
        do: assert(Event.build(i, l, f, a, %{c | source_ip: ip}) == @error)

    for ip <- [nil, "127.0.0.1", ["127.0.0.1", "::1"], [nil], ["::1" | :improper]],
        do: assert(Event.decode(Map.put(record().display, "source_ip", ip)) == @error)
  end

  test "sequence bounds, exact tenant genesis, reason bound and request metadata cannot select identity" do
    {i, l, f, a, c} = fixture()

    for n <- [0, -1, @max + 1, 1.0],
        do: assert(Event.build(i, l, f, a, %{c | sequence: n}) == @error)

    assert Event.build(i, l, f, a, %{c | previous_event_sha256: String.duplicate("e", 64)}) ==
             @error

    assert Event.build(i, l, f, a, %{c | previous_state_sha256: String.duplicate("f", 64)}) ==
             @error

    assert Event.build(i, l, f, a, %{c | reason: String.duplicate("é", 257)}) == @error
    assert {:ok, _} = Event.build(i, l, f, a, %{c | reason: String.duplicate("é", 256)})
    assert {:ok, _} = Event.build(i, l, f, a, %{c | reason: ""})
    assert Event.build(i, l, f, a, %{c | reason: <<255>>}) == @error

    assert Event.build(
             i,
             %{l | request_id: "http-caller-id"},
             %{f | request_id: "http-caller-id"},
             a,
             c
           ) == @error

    assert {:ok, _} =
             Event.build(i, l, f, a, %{
               c
               | sequence: @max,
                 previous_event_sha256: String.duplicate("e", 64)
             })
  end

  test "request hashes retain signed target envelope and reason while retry metadata is excluded" do
    {i, l, f, a, c} = fixture()
    original = record()

    assert {:ok, changed} =
             Event.build(
               i,
               %{l | request_id: String.duplicate("e", 32), checked_at: 101},
               %{f | request_id: String.duplicate("e", 32), checked_at: 103},
               a,
               %{c | source_ip: "::1"}
             )

    assert original.display["request_sha256"] == changed.display["request_sha256"]
    refute original.event_sha256 == changed.event_sha256
    target = original.display["target"]

    for {new_target, envelope, reason} <- [
          {set(target, 4, "android"), a.envelope_sha256, c.reason},
          {target, String.duplicate("e", 64), c.reason},
          {target, a.envelope_sha256, c.reason <> " "}
        ] do
      assert {:ok, hash} = Event.request_hash(new_target, envelope, reason)
      refute hash == original.display["request_sha256"]
    end

    assert Event.request_hash(target ++ [1], a.envelope_sha256, c.reason) == @error
    assert Event.genesis("*", "project") == @error
  end

  test "created and unchanged records advance chain while unchanged preserves exact state" do
    {i, l, f, a, c} = fixture()
    first = record()

    next = %{
      c
      | sequence: 2,
        outcome: "unchanged",
        previous_state_sha256: first.display["current_state_sha256"],
        previous_event_sha256: first.event_sha256
    }

    assert {:ok, second} = Event.build(i, l, f, a, next)
    assert second.display["current_state_sha256"] == first.display["current_state_sha256"]
    refute second.event_sha256 == first.event_sha256
    assert Event.validate_edge(second, first) == :ok
    assert Event.validate_edge(second, nil) == @error
    assert Event.validate_edge(first, second) == @error

    assert {:ok, third} =
             Event.build(i, l, f, a, %{
               next
               | sequence: 3,
                 previous_event_sha256: second.event_sha256,
                 outcome: "created"
             })

    refute third.display["current_state_sha256"] == second.display["current_state_sha256"]
    assert Event.validate_edge(third, second) == :ok
    assert Event.validate_edge(third, first) == @error

    for key <- [:previous_state_sha256, :previous_event_sha256] do
      assert {:ok, broken} =
               Event.build(i, l, f, a, Map.put(next, key, String.duplicate("f", 64)))

      assert Event.validate_edge(broken, first) == @error
    end

    assert {:ok, unchanged_genesis} = Event.build(i, l, f, a, %{c | outcome: "unchanged"})
    assert unchanged_genesis.display["current_state_sha256"] == c.previous_state_sha256
  end

  test "membership count, UTF8 byte ordering, unique IDs, role scope binding and live windows" do
    {i, l, f, a, c} = fixture()
    member = hd(f.memberships)

    members =
      for n <- 1..64,
          do: %{member | id: "member-" <> String.pad_leading(Integer.to_string(n), 2, "0")}

    assert {:ok, _} =
             Event.build(i, %{l | memberships: members}, %{f | memberships: members}, a, c)

    for bad <- [
          [],
          members ++ [%{member | id: "member-65"}],
          Enum.reverse(members),
          [member, member],
          [member | :improper]
        ],
        do: assert(Event.build(i, l, %{f | memberships: bad}, a, c) == @error)

    for changes <- [
          %{role: "viewer"},
          %{role: "release_manager"},
          %{active: false},
          %{not_before: 103},
          %{expires_at: 102},
          %{revision: 0},
          %{principal_id: "other"},
          %{project_binding: :all_projects},
          %{scope: %Scope{organization_id: "other", project_id: "project"}}
        ],
        do:
          assert(
            Event.build(i, l, %{f | memberships: [Map.merge(member, changes)]}, a, c) == @error
          )
  end

  test "maximum-width 64-row projection fits output budget and oversized retained bytes fail closed" do
    {i, l, f, a, c} = fixture()
    long = String.duplicate("x", 128)

    target = %Scope{
      organization_id: long,
      project_id: long,
      application_id: long,
      environment_id: long
    }

    artifact = %{
      a
      | organization_id: long,
        project_id: long,
        application_id: long,
        environment_id: long
    }

    member = hd(f.memberships)

    members =
      for n <- 1..64,
          do: %{
            member
            | id: String.pad_leading(Integer.to_string(n), 128, "0"),
              scope: %Scope{organization_id: long, project_id: long}
          }

    transform = fn s ->
      %{
        s
        | target: target,
          memberships: members,
          organization_head: %{organization_id: long, revision: 7},
          project_head: %{organization_id: long, project_id: long, revision: 8}
      }
    end

    {:ok, genesis} = Event.genesis(long, long)
    # Current grammar caps this event below 65,536 bytes; the shared encoder is
    # still the hard byte-budget guard for this and future bounded projections.
    assert {:ok, result} =
             Event.build(i, transform.(l), transform.(f), artifact, %{
               c
               | previous_state_sha256: genesis,
                 reason: String.duplicate("r", 512)
             })

    assert byte_size(result.event_cbor) < 65_536
    assert byte_size(result.event_cbor) > 29_000

    assert ArtifactCBOR.encode(
             Enum.map(@fields, &result.display[&1]),
             byte_size(result.event_cbor) - 1
           ) == {:error, :limit_exceeded}

    assert Event.validate_row(%{result | event_cbor: String.duplicate("x", 65_537)}) == @error
  end

  test "display and retained rows are closed exact schemas with no v1 byte coercion" do
    result = record()

    for key <- Map.keys(result.display),
        do: assert(Event.decode(Map.delete(result.display, key)) == @error)

    assert Event.decode(Map.put(result.display, "unknown", 1)) == @error
    assert Event.decode(Map.put(result.display, "audit_schema", 1)) == @error

    assert Event.decode(Map.new(result.display, fn {k, v} -> {String.to_atom(k), v} end)) ==
             @error

    assert Event.validate_row(Map.put(Map.from_struct(result), :unknown, 1)) == @error
    assert Event.validate_row(Map.put(result, :unknown, 1)) == @error

    for key <- [:event_cbor, :event_sha256, :display] do
      forged = result |> Map.delete(key) |> Map.put(:unknown, 1)
      assert Event.validate_row(forged) == @error
      assert Event.validate_edge(forged, nil) == @error
    end

    for key <- [:event_cbor, :event_sha256, :display],
        do: assert(Event.validate_row(Map.delete(Map.from_struct(result), key)) == @error)

    assert Event.validate_row(%{result | event_cbor: result.event_cbor <> <<0>>}) == @error
    assert Event.validate_row(%{result | event_sha256: String.duplicate("f", 64)}) == @error

    assert Event.validate_row(%{result | display: Map.put(result.display, "reason", "changed")}) ==
             @error

    assert Event.decode(%{"schema" => 1}) == @error
    assert is_struct(result, Record)
  end

  test "all fixed nested arrays reject missing extra improper values before encoding" do
    d = record().display

    for field <- ["tenant", "actor", "authorization", "target"],
        value <- [[], [nil], Map.new(), :invalid] do
      assert Event.decode(Map.put(d, field, value)) == @error
    end

    for field <- ["tenant", "actor", "authorization", "target"] do
      array = d[field]
      assert Event.decode(Map.put(d, field, tl(array))) == @error
      assert Event.decode(Map.put(d, field, array ++ [1])) == @error
      assert Event.decode(Map.put(d, field, [hd(array) | :improper])) == @error
    end

    for index <- 2..6 do
      array = Enum.at(d["authorization"], index)

      for bad <- [tl(array), array ++ [1], [hd(array) | :improper]],
          do: assert(Event.decode(changed(d, "authorization", index, bad)) == @error)
    end

    members = List.last(d["authorization"])

    for bad <- [
          [],
          members ++ members,
          [hd(members) | :improper],
          [hd(members) ++ [1]],
          [tl(hd(members))]
        ],
        do: assert(Event.decode(changed(d, "authorization", 10, bad)) == @error)
  end

  test "semantic nested mutations fail even after independently recomputing event hash" do
    d = record().display

    bad_actor =
      for {index, value} <- [
            {0, "*"},
            {1, "service"},
            {2, ""},
            {3, 0},
            {3, 2_147_483_648},
            {4, "hash"},
            {5, String.duplicate("A", 64)},
            {9, "*"},
            {10, 1001},
            {11, 102}
          ],
          do: changed(d, "actor", index, value)

    bad_auth =
      for {index, value} <- [
            {0, 103},
            {1, 106},
            {2, [0, true]},
            {3, [3, false]},
            {4, [4, true, 81]},
            {5, [5, true, 81, []]},
            {5, [5, true, 50, [102]]},
            {6, [6, true, 40, [40]]},
            {7, 0},
            {8, @max + 1},
            {9, "mixer.artifact.read"}
          ],
          do: changed(d, "authorization", index, value)

    member = hd(List.last(d["authorization"]))

    bad_members =
      for {index, value} <- [
            {0, "*"},
            {1, "viewer"},
            {2, 0},
            {3, "other"},
            {4, ["other"]},
            {4, ["project", "extra"]},
            {5, "all_projects"},
            {6, false},
            {7, 103},
            {8, [102]},
            {8, [1, 2]}
          ],
          do: changed(d, "authorization", 10, [set(member, index, value)])

    bad_scalars =
      for {key, value} <- [
            {"sequence", 0},
            {"outcome", "rejected"},
            {"action", "artifact.read"},
            {"request_id", String.duplicate("F", 32)},
            {"recorded_at", 101},
            {"previous_state_sha256", String.duplicate("f", 64)},
            {"current_state_sha256", String.duplicate("f", 64)},
            {"previous_event_sha256", String.duplicate("f", 64)},
            {"request_sha256", String.duplicate("f", 64)},
            {"envelope_sha256", String.duplicate("f", 64)}
          ],
          do: Map.put(d, key, value)

    for altered <- bad_actor ++ bad_auth ++ bad_members ++ bad_scalars,
        do: assert(Event.decode(sealed(altered)) == @error)
  end
end
