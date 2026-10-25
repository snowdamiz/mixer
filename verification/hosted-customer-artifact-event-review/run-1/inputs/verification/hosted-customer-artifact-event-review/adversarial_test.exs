defmodule MixerHosted.CustomerArtifactEventIndependentReviewTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Audit.CustomerArtifactEvent, as: Event
  alias MixerHosted.Audit.CustomerArtifactEvent.Record
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHosted.Protocol.ArtifactCBOR

  @error {:error, :invalid_audit_event}
  @max 9_007_199_254_740_991
  @fields ~w(audit_schema sequence tenant actor authorization target action outcome reason request_id source_ip recorded_at previous_state_sha256 current_state_sha256 previous_event_sha256 request_sha256 envelope_sha256)

  defp oracle, do: System.fetch_env!("MIXER_REVIEW_ORACLE") |> File.read!() |> Jason.decode!()
  defp plain(value), do: :crypto.hash(:sha256, value) |> Base.encode16(case: :lower)
  defp digest(field, value), do: plain("mixer.hosted.customer." <> field <> ".v2\0" <> value)
  defp set(value, index, replacement), do: List.replace_at(value, index, replacement)

  defp fixture do
    o = oracle()
    r = o["raw"]
    v = o["values"]
    [org, project, app, env, platform, runtime, manifest, payload] = Enum.at(v, 5)
    i = struct!(VerifiedIdentity, Map.new(r, fn {k, v} -> {String.to_existing_atom(k), v} end)
      |> Map.merge(%{identity_class: :human, scopes: ["mixer.artifact.upload", "unrecorded:雪"]}))
    locked = Enum.at(v, 4) |> hd()
    fresh = Enum.at(v, 11)
    member = %{id: "00-org", principal_id: "principal:✓", role: "developer",
      scope: %Scope{organization_id: org}, project_binding: :all_projects,
      active: true, not_before: locked - 10, expires_at: nil, revision: 17}
    newer = %{member | id: "équipe", role: "owner", revision: 18,
      scope: %Scope{organization_id: org, project_id: project},
      project_binding: :exact_project, not_before: fresh, expires_at: fresh + 1}
    s = %{request_id: Enum.at(v, 9), profile: %{id: i.profile_id, version: i.profile_version,
        issuer: i.issuer, client_id: i.client_id, identity_class: "human", active: true, state_revision: 11},
      binding: %{profile_id: i.profile_id, profile_version: i.profile_version,
        subject_digest: plain(i.subject), identity_class: "human", principal_id: member.principal_id,
        active: true, revision: 12},
      principal: %{id: member.principal_id, identity_class: :human, active: true,
        not_before: locked - 20, revision: 13},
      credential: %{profile_id: i.profile_id, profile_version: i.profile_version,
        reference: i.credential_ref, principal_id: member.principal_id, family_id: "family/雪",
        active: true, not_before: locked - 15, expires_at: nil, revision: 14},
      family: %{id: "family/雪", profile_id: i.profile_id, profile_version: i.profile_version,
        principal_id: member.principal_id, active: true, not_before: locked - 15,
        expires_at: fresh + 100, revision: 15},
      memberships: [member], organization_head: %{organization_id: org, revision: 16},
      project_head: %{organization_id: org, project_id: project, revision: 19},
      identity: identity_snapshot(i), action: "artifact.upload",
      target: %Scope{organization_id: org, project_id: project, application_id: app, environment_id: env},
      checked_at: locked}
    a = %{organization_id: org, project_id: project, application_id: app, environment_id: env,
      platform: platform, runtime_sha256: runtime, manifest_sha256: manifest,
      payload_sha256: payload, envelope_sha256: Enum.at(v, 16)}
    c = %{sequence: 1, previous_state_sha256: o["hashes"]["genesis"], previous_event_sha256: "",
      outcome: "created", reason: Enum.at(v, 8), source_ip: "192.0.2.10"}
    {i, s, %{s | checked_at: fresh, memberships: [member, newer]}, a, c}
  end

  defp identity_snapshot(i), do: i |> Map.from_struct() |> Map.delete(:subject) |> Map.put(:subject_digest, plain(i.subject))
  defp build({i, l, f, a, c}), do: Event.build(i, l, f, a, c)
  defp record, do: elem(build(fixture()), 1)
  defp seal(d) do
    {:ok, bytes} = ArtifactCBOR.encode(Enum.map(@fields, &Map.fetch!(d, &1)))
    Map.put(d, "event_sha256", digest("audit", bytes))
  end
  defp put_array(d, field, index, value), do: Map.update!(d, field, &set(&1, index, value))

  test "independent RFC primitive oracle, raw Unicode fixture, CBOR and every hash namespace" do
    o = oracle()
    assert o["primitive_vectors"] == 18
    assert {:ok, r} = build(fixture())
    assert Base.encode16(r.event_cbor, case: :lower) == o["event_hex"]
    assert r.event_sha256 == o["hashes"]["event"]
    assert Enum.map(@fields, &r.display[&1]) == o["values"]
    assert Event.decode(r.display) == {:ok, r}
    assert Event.validate_row(r) == :ok
    assert Event.validate_row(Map.from_struct(r)) == :ok
    assert Event.validate_edge(r, nil) == :ok
    assert Event.genesis("org:é", "project:雪") == {:ok, o["hashes"]["genesis"]}
    assert Event.request_hash(r.display["target"], r.display["envelope_sha256"], r.display["reason"]) == {:ok, o["hashes"]["request"]}
    for {field, index} <- [{"binding_key", 4}, {"issuer", 5}, {"subject", 6}, {"client", 7}, {"credential_ref", 8}] do
      assert Enum.at(r.display["actor"], index) == o["hashes"][field]
    end
    for key <- ["subject_prehashed", "subject_printable_zero"],
      do: refute(Enum.at(r.display["actor"], 6) == o["known_wrong_hashes"][key])
    refute Enum.at(r.display["actor"], 4) == o["known_wrong_hashes"]["binding_prehashed"]
    for raw <- Map.take(o["raw"], ~w(issuer subject client_id credential_ref)) |> Map.values(),
      do: assert(:binary.match(r.event_cbor, raw) == :nomatch)
  end

  test "fully coherent forgeable snapshot and row values remain data, with no authenticity claim" do
    {i, l, f, a, c} = fixture()
    # There is deliberately no transaction handle or signature verifier in this API.
    assert {:ok, _} = Event.build(i, l, f, a, c)
    d = record().display |> put_array("actor", 0, "invented-principal") |> seal()
    assert {:ok, forged} = Event.decode(d)
    assert Event.validate_row(forged) == :ok
    assert Event.validate_edge(forged, nil) == :ok
    assert Event.build(Map.from_struct(i), l, f, a, c) == @error
    for field <- [:issuer, :subject, :client_id, :credential_ref, :profile_id] do
      assert Event.build(Map.update!(i, field, &(&1 <> "/changed")), l, f, a, c) == @error
    end
  end

  test "immutable locked-to-fresh linkage is exact, including identity and request" do
    {i, l, f, a, c} = fixture()
    for key <- Map.keys(l) -- [:checked_at, :memberships] do
      assert Event.build(i, l, Map.put(f, key, :changed), a, c) == @error
    end
    assert {:ok, _} = Event.build(i, l, %{f | memberships: l.memberships}, a, c)
    for key <- [:profile, :binding, :principal, :credential, :family] do
      for at <- [:locked, :fresh] do
        changed = put_in(if(at == :locked, do: l, else: f), [key, :active], false)
        assert Event.build(i, if(at == :locked, do: changed, else: l), if(at == :fresh, do: changed, else: f), a, c) == @error
      end
    end
    for field <- [:profile, :binding, :principal, :credential, :family, :identity, :organization_head, :project_head] do
      for nested_key <- Map.keys(l[field]) do
        assert Event.build(i, Map.put(l, field, Map.delete(l[field], nested_key)), f, a, c) == @error
        assert Event.build(i, l, Map.put(f, field, Map.delete(f[field], nested_key)), a, c) == @error
      end
      assert Event.build(i, Map.put(l, field, Map.put(l[field], :extra, 1)), f, a, c) == @error
      assert Event.build(i, l, Map.put(f, field, Map.put(f[field], :extra, 1)), a, c) == @error
    end
  end

  test "time boundary inclusivity and principal, token, credential, family and membership windows" do
    {i, l, f, a, c} = fixture()
    now = l.checked_at
    for elapsed <- [0, 5], do: assert(match?({:ok, _}, Event.build(i, l, %{f | checked_at: now + elapsed, memberships: l.memberships}, a, c)))
    for elapsed <- [-1, 6], do: assert(Event.build(i, l, %{f | checked_at: now + elapsed}, a, c) == @error)
    for field <- [:principal, :credential, :family] do
      ll = put_in(l, [field, :not_before], now + 1)
      ff = put_in(f, [field, :not_before], now + 1)
      assert Event.build(i, ll, ff, a, c) == @error
    end
    for field <- [:credential, :family], end_at <- [now, f.checked_at] do
      assert Event.build(i, put_in(l, [field, :expires_at], end_at), put_in(f, [field, :expires_at], end_at), a, c) == @error
    end
    for expires <- [f.checked_at, f.checked_at + 1] do
      ii = %{i | expires_at: expires}
      result = Event.build(ii, %{l | identity: identity_snapshot(ii)}, %{f | identity: identity_snapshot(ii)}, a, c)
      if expires == f.checked_at, do: assert(result == @error), else: assert(match?({:ok, _}, result))
    end
    for issued <- [now + 30, now + 31] do
      ii = %{i | issued_at: issued}
      result = Event.build(ii, %{l | identity: identity_snapshot(ii)}, %{f | identity: identity_snapshot(ii)}, a, c)
      if issued == now + 30, do: assert(match?({:ok, _}, result)), else: assert(result == @error)
    end
  end

  test "closed maps, exact arities, target ancestry, optional arrays and retained row equality" do
    {i, l, f, a, c} = fixture()
    for {slot, value} <- [{1, l}, {2, f}, {3, a}, {4, c}], key <- Map.keys(value) do
      assert fixture() |> put_elem(slot, Map.delete(value, key)) |> build() == @error
      assert fixture() |> put_elem(slot, Map.put(value, :unknown, true)) |> build() == @error
    end
    for field <- [:organization_id, :project_id, :application_id, :environment_id],
      do: assert(Event.build(i, l, f, Map.put(a, field, "foreign"), c) == @error)
    d = record().display
    for key <- Map.keys(d), do: assert(Event.decode(Map.delete(d, key)) == @error)
    assert Event.decode(Map.put(d, "unrecognized", 0)) == @error
    for field <- ["tenant", "actor", "authorization", "target"],
        changed <- [tl(d[field]), d[field] ++ [0], [hd(d[field]) | :improper]] do
      assert Event.decode(Map.put(d, field, changed)) == @error
    end
    for index <- 2..6, changed <- [[], Enum.at(d["authorization"], index) ++ [0], [:bad | :improper]],
      do: assert(Event.decode(put_array(d, "authorization", index, changed)) == @error)
    for bad <- [nil, [nil], ["192.0.2.10", "::1"], ["::1" | :improper]],
      do: assert(Event.decode(Map.put(d, "source_ip", bad)) == @error)
    r = record()
    for changed <- [%{r | event_cbor: r.event_cbor <> <<0>>}, %{r | event_sha256: String.duplicate("f", 64)},
        %{r | display: Map.put(d, "reason", "changed")}, Map.put(r, :extra, true), Map.delete(r, :event_cbor)],
      do: assert(Event.validate_row(changed) == @error)
  end

  test "resealed semantic tampering cannot bypass roles, scope, active state or time fences" do
    d = record().display
    auth_mutations = [{0, d["recorded_at"] + 1}, {1, d["recorded_at"] + 1}, {2, [0, true]},
      {3, [12, false]}, {4, [13, true, d["recorded_at"]]}, {5, [14, true, 0, [d["recorded_at"]]]},
      {6, [15, true, 0, [0]]}, {7, @max + 1}, {8, 0}, {9, "mixer.audit.read"}]
    for {index, value} <- auth_mutations, do: assert(Event.decode(d |> put_array("authorization", index, value) |> seal()) == @error)
    actor_mutations = [{0, "*"}, {1, "service"}, {2, ""}, {3, 2147483648}, {4, String.duplicate("F", 64)},
      {9, "*"}, {10, d["recorded_at"] + 26}, {11, d["recorded_at"]}]
    for {index, value} <- actor_mutations, do: assert(Event.decode(d |> put_array("actor", index, value) |> seal()) == @error)
    [m | _] = List.last(d["authorization"])
    changes = [{0, "*"}, {1, "viewer"}, {1, "release_manager"}, {2, 0}, {3, "foreign"},
      {4, ["foreign"]}, {4, ["project:雪", "extra"]}, {5, "exact_project"}, {6, false},
      {7, d["recorded_at"] + 1}, {8, [d["recorded_at"]]}, {8, [1, 2]}]
    for {index, value} <- changes, do: assert(Event.decode(d |> put_array("authorization", 10, [set(m, index, value)]) |> seal()) == @error)
    for {key, value} <- [{"audit_schema", 1}, {"action", "artifact.read"}, {"outcome", "rejected"},
        {"recorded_at", d["recorded_at"] - 1}, {"request_id", String.duplicate("E", 32)},
        {"previous_state_sha256", String.duplicate("f", 64)}, {"request_sha256", String.duplicate("f", 64)},
        {"current_state_sha256", String.duplicate("f", 64)}],
      do: assert(Event.decode(d |> Map.put(key, value) |> seal()) == @error)
  end

  test "created and unchanged chain and retries have separate exact identities" do
    {i, l, f, a, c} = fixture()
    first = record()
    c2 = %{c | sequence: 2, previous_state_sha256: first.display["current_state_sha256"],
      previous_event_sha256: first.event_sha256, outcome: "unchanged"}
    assert {:ok, second} = Event.build(i, l, f, a, c2)
    assert second.display["current_state_sha256"] == first.display["current_state_sha256"]
    refute second.event_sha256 == first.event_sha256
    assert Event.validate_edge(second, first) == :ok
    assert Event.validate_edge(second, nil) == @error
    assert Event.validate_edge(first, second) == @error
    for field <- [:previous_state_sha256, :previous_event_sha256] do
      assert {:ok, bad} = Event.build(i, l, f, a, Map.put(c2, field, String.duplicate("9", 64)))
      assert Event.validate_edge(bad, first) == @error
    end
    assert {:ok, third} = Event.build(i, l, f, a, %{c2 | sequence: 3, previous_event_sha256: second.event_sha256, outcome: "created"})
    assert Event.validate_edge(third, second) == :ok
    refute third.display["current_state_sha256"] == second.display["current_state_sha256"]
    assert Event.validate_edge(third, first) == @error
    assert {:ok, retry} = Event.build(i, %{l | request_id: String.duplicate("a", 32)}, %{f | request_id: String.duplicate("a", 32)}, a, %{c | source_ip: nil})
    assert retry.display["request_sha256"] == first.display["request_sha256"]
    refute retry.event_sha256 == first.event_sha256
    changed_i = %{i | credential_ref: "new-credential"}
    sync = fn s -> %{s | identity: identity_snapshot(changed_i), credential: %{s.credential | reference: changed_i.credential_ref}} end
    assert {:ok, refreshed} = Event.build(changed_i, sync.(l), sync.(f), a, c)
    assert refreshed.display["request_sha256"] == first.display["request_sha256"]
    refute refreshed.display["actor"] == first.display["actor"]
    for target <- for(index <- 0..7, do: set(first.display["target"], index, if(index == 4, do: "ios", else: if(index >= 5, do: String.duplicate("8", 64), else: "changed")))) do
      assert {:ok, hash} = Event.request_hash(target, a.envelope_sha256, c.reason)
      refute hash == first.display["request_sha256"]
    end
    for {envelope, reason} <- [{String.duplicate("5", 64), c.reason}, {a.envelope_sha256, c.reason <> " "}] do
      assert {:ok, hash} = Event.request_hash(first.display["target"], envelope, reason)
      refute hash == first.display["request_sha256"]
    end
  end

  test "64 maximum width memberships and scalar limits are enforced before unbounded work" do
    {i, l, f, a, c} = fixture()
    member = hd(l.memberships)
    members = for n <- 1..64, do: %{member | id: String.pad_leading(Integer.to_string(n), 128, "0")}
    assert {:ok, max_record} = Event.build(i, %{l | memberships: members}, %{f | memberships: members}, a, %{c | reason: String.duplicate("雪", 170) <> "ab"})
    assert byte_size(max_record.event_cbor) < 65_536
    for invalid <- [members ++ [member], Enum.reverse(members), [member, member], [], [member | :improper]],
      do: assert(Event.build(i, l, %{f | memberships: invalid}, a, c) == @error)
    assert Event.build(i, l, f, a, %{c | reason: String.duplicate("雪", 171)}) == @error
    assert Event.validate_row(%{max_record | event_cbor: :binary.copy("a", 65_537)}) == @error
    for number <- [0, -1, @max + 1, 1.0], do: assert(Event.build(i, l, f, a, %{c | sequence: number}) == @error)
    assert {:ok, _} = Event.build(i, l, f, a, %{c | sequence: @max, previous_event_sha256: String.duplicate("a", 64)})
    for text <- [String.duplicate("x", 129), "*", <<255>>, "bad\n", <<0>>] do
      assert Event.genesis(text, "project") == @error
      assert Event.build(i, l, f, %{a | application_id: text}, c) == @error
    end
  end

  test "public APIs reject arbitrary hostile terms without raising or traversing huge invalid tails" do
    {i, l, f, a, c} = fixture()
    d = record().display
    large = List.duplicate(:invalid, 100_000)
    deep = Enum.reduce(1..100, :invalid, fn _, acc -> [acc] end)
    hostile = [:invalid, nil, false, -1, 0.25, <<255>>, <<1::1>>, %{}, {:tuple, 1}, self(), make_ref(), fn -> :ok end,
      [1 | :improper], large, deep]
    for bad <- hostile do
      assert Event.decode(bad) == @error
      assert Event.validate_row(bad) == @error
      assert Event.validate_edge(bad, nil) == @error
      assert Event.genesis(bad, bad) == @error
      assert Event.request_hash(bad, bad, bad) == @error
      for slot <- 0..4, do: assert(fixture() |> put_elem(slot, bad) |> build() == @error)
    end
    impossible = [:invalid, <<255>>, <<1::1>>, %{}, {:tuple, 1}, self(), make_ref(), fn -> :ok end, large, deep]
    for key <- Map.keys(d), bad <- impossible do
      assert Event.decode(Map.put(d, key, bad)) == @error
    end
    for field <- ["actor", "authorization", "target"], index <- 0..(length(d[field]) - 1), bad <- impossible do
      assert Event.decode(put_array(d, field, index, bad)) == @error
    end
    for bad <- hostile do
      assert Event.build(i, l, %{f | memberships: [hd(l.memberships) | bad]}, a, c) == @error
    end
    # The traversals inspect <=65 membership cons cells and bounded scalar bytes;
    # already allocated caller terms and total BEAM memory are outside the claim.
    assert is_struct(record(), Record)
  end
end
