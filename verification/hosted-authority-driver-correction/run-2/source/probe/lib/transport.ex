defmodule MixerHosted.AuthorityDriver.Rejected do
  defexception [:reason]
  def message(_), do: "authority driver rejected"
end

defmodule MixerHosted.AuthorityDriver.Envelope do
  alias MixerHosted.Identity.{ConfiguredVerifier, VerifiedIdentity}
  @enforce_keys [:identity, :authentication_completed_at]
  defstruct @enforce_keys
  # Capture immediately after the accepted verifier returns; no body/signature work here.
  def authenticate(token, now) do
    case ConfiguredVerifier.authenticate(token, now) do
      {:ok, %VerifiedIdentity{} = identity} ->
        {:ok,
         %__MODULE__{identity: identity, authentication_completed_at: System.system_time(:second)}}

      error ->
        error
    end
  end
end

defmodule MixerHosted.AuthorityDriver.Transport do
  alias MixerHosted.AuthorityDriver.{Envelope, Rejected}
  alias MixerHosted.Identity.VerifiedIdentity
  @max 9_007_199_254_740_991
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @scopes ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read)
  @ik ~w(profile_id profile_version issuer subject client_id credential_sha256 issued_at expires_at identity_class scopes authentication_completed_at)a
  @tk ~w(action organization project app environment platform runtime_sha256 manifest_sha256)a
  @xk ~w(backend full_xid database_name runtime_role nonce deadline)a
  @ak ~w(principal_id binding_id family_id profile_revision principal_revision family_revision organization_revision project_revision lock_statement_at)a
  @dk ~w(outcome principal_id binding_id family_id decision_at profile_revision principal_revision family_revision organization_revision project_revision)a
  @isql "ROW($1::text,$2::int4,$3::text,$4::text,$5::text,$6::bytea,$7::numeric,$8::numeric,$9::text,$10::text[],$11::numeric)::mixer_authz.verified_identity_v1"
  @tsql "ROW($12::text,$13::text,$14::text,$15::text,$16::text,$17::text,$18::bytea,$19::bytea)::mixer_authz.target_v1"
  @xsql "ROW($20::int4,$21::text,$22::name,$23::name,$24::text,$25::timestamptz)::mixer_authz.transaction_identity_v1"
  @asql "ROW(#{@isql},#{@tsql},#{@xsql},$26::uuid,$27::uuid,$28::uuid,$29::int8,$30::int8,$31::int8,$32::int8,$33::int8,$34::timestamptz)::mixer_authz.admission_v1"
  @admission_fields Enum.map_join(@ik, ",", &"(r.identity).#{&1}") <>
                      "," <>
                      Enum.map_join(@tk, ",", &"(r.target).#{&1}") <>
                      "," <>
                      Enum.map_join(@xk, ",", &"(r.transaction_identity).#{&1}") <>
                      "," <>
                      Enum.map_join(@ak, ",", &"r.#{&1}")
  @decision_fields Enum.map_join(@dk, ",", &"r.#{&1}") <>
                     ",ARRAY(SELECT m.lifecycle_id FROM unnest(r.memberships) m),ARRAY(SELECT m.role FROM unnest(r.memberships) m),ARRAY(SELECT m.revision FROM unnest(r.memberships) m)"
  # The one VOLATILE function is a FROM relation, evaluated once. Never SELECT (f()).*.
  def query(:lookup),
    do:
      "SELECT #{@admission_fields} FROM mixer_authz.lookup_admission(#{@isql},#{@tsql},#{@xsql}) AS r"

  def query(:lock),
    do:
      "SELECT #{@admission_fields} FROM mixer_authz.lock_admission_rows(#{@isql},#{@tsql},#{@asql},#{@xsql}) AS r"

  def query(:decision),
    do:
      "SELECT #{@decision_fields} FROM mixer_authz.decide_current(#{@isql},#{@tsql},#{@asql},#{@xsql}) AS r"

  def identity(%Envelope{
        identity: %VerifiedIdentity{} = i,
        authentication_completed_at: completion
      }) do
    assert(
      text?(i.profile_id, 128) and text?(i.issuer, 2048) and text?(i.subject, 256) and
        text?(i.client_id, 256) and text?(i.credential_ref, 256)
    )

    assert(is_integer(i.profile_version) and i.profile_version in 1..2_147_483_647)

    assert(
      uint?(i.issued_at) and uint?(i.expires_at) and uint?(completion) and
        i.issued_at < i.expires_at and completion < i.expires_at
    )

    assert(
      i.identity_class == :human and is_list(i.scopes) and length(i.scopes) <= 3 and
        Enum.uniq(i.scopes) == i.scopes and Enum.all?(i.scopes, &(&1 in @scopes))
    )

    %{
      profile_id: i.profile_id,
      profile_version: i.profile_version,
      issuer: i.issuer,
      subject: i.subject,
      client_id: i.client_id,
      credential_sha256: :crypto.hash(:sha256, i.credential_ref),
      issued_at: i.issued_at,
      expires_at: i.expires_at,
      identity_class: "human",
      scopes: i.scopes,
      authentication_completed_at: completion
    }
  end

  def identity(_), do: raise(Rejected, reason: :invalid_transport)

  def target(t) when is_map(t) do
    assert(Enum.sort(Map.keys(t)) == Enum.sort(@tk))

    assert(
      t.action in ~w(artifact.read artifact.upload audit.read) and id?(t.organization) and
        id?(t.project)
    )

    if t.action == "audit.read" do
      assert(
        Enum.all?(
          [t.app, t.environment, t.platform, t.runtime_sha256, t.manifest_sha256],
          &is_nil/1
        )
      )
    else
      assert(
        id?(t.app) and id?(t.environment) and t.platform in ~w(ios android) and
          digest?(t.runtime_sha256) and digest?(t.manifest_sha256)
      )
    end

    t
  end

  def target(_), do: raise(Rejected, reason: :invalid_transport)

  def params(i, t, x, a \\ nil) do
    Enum.map(@ik, fn k ->
      if k in [:issued_at, :expires_at, :authentication_completed_at],
        do: Decimal.new(Map.fetch!(i, k)),
        else: Map.fetch!(i, k)
    end) ++
      Enum.map(@tk, &Map.fetch!(t, &1)) ++
      Enum.map(@xk, &Map.fetch!(x, &1)) ++
      if(a, do: Enum.map(@ak, &Map.fetch!(a, &1)), else: [])
  end

  def admission(%{rows: [row], num_rows: 1}, i, t, x, stage) when length(row) == 34 do
    {iv, rest} = Enum.split(row, 11)
    {tv, rest} = Enum.split(rest, 8)
    {xv, av} = Enum.split(rest, 6)

    ii =
      Map.new(Enum.zip(@ik, iv))
      |> Map.update!(:issued_at, &integer!/1)
      |> Map.update!(:expires_at, &integer!/1)
      |> Map.update!(:authentication_completed_at, &integer!/1)

    tt = Map.new(Enum.zip(@tk, tv))
    xx = Map.new(Enum.zip(@xk, xv))
    a = Map.new(Enum.zip(@ak, av))
    assert(ii == i and tt == t and xx == x)
    assert(Enum.all?([a.principal_id, a.binding_id, a.family_id], &uuid?/1))

    revisions =
      Enum.map(
        [
          :profile_revision,
          :principal_revision,
          :family_revision,
          :organization_revision,
          :project_revision
        ],
        &Map.fetch!(a, &1)
      )

    if stage == :lookup,
      do: assert(Enum.all?(revisions, &is_nil/1) and a.lock_statement_at == nil),
      else:
        assert(Enum.all?(revisions, &revision?/1) and match?(%DateTime{}, a.lock_statement_at))

    Map.merge(a, %{identity: ii, target: tt, transaction_identity: xx})
  end

  def admission(_, _, _, _, _), do: raise(Rejected, reason: :result_shape)

  def decision(%{rows: [row], num_rows: 1}, a) when length(row) == 13 do
    {scalar, [ids, roles, revs]} = Enum.split(row, 10)
    d = Map.new(Enum.zip(@dk, scalar)) |> Map.update!(:decision_at, &integer!/1)
    assert(d.outcome in ~w(allowed forbidden not_found authorization_unavailable))

    assert(
      is_list(ids) and is_list(roles) and is_list(revs) and length(ids) <= 64 and
        length(ids) == length(roles) and length(ids) == length(revs)
    )

    members =
      Enum.zip([ids, roles, revs])
      |> Enum.map(fn {id, role, rev} ->
        assert(uuid?(id) and role in @roles and revision?(rev))
        %{lifecycle_id: id, role: role, revision: rev}
      end)

    assert(ids == Enum.sort(ids) and length(Enum.uniq(ids)) == length(ids))

    assert(
      Enum.all?(
        [
          :principal_id,
          :binding_id,
          :family_id,
          :profile_revision,
          :principal_revision,
          :family_revision,
          :organization_revision,
          :project_revision
        ],
        &(Map.fetch!(a, &1) == Map.fetch!(d, &1))
      )
    )

    Map.put(d, :memberships, members)
  end

  def decision(_, _), do: raise(Rejected, reason: :result_shape)

  def integer!(%Decimal{} = d) do
    n = Decimal.to_integer(d)
    assert(Decimal.equal?(d, Decimal.new(n)) and uint?(n))
    n
  end

  def integer!(n) when is_integer(n),
    do:
      (
        assert(uint?(n))
        n
      )

  def integer!(_), do: raise(Rejected, reason: :result_shape)
  def assert(true), do: :ok
  def assert(_), do: raise(Rejected, reason: :invalid_transport)
  defp uint?(n), do: is_integer(n) and n >= 0 and n <= @max
  defp revision?(n), do: is_integer(n) and n > 0 and n <= 9_223_372_036_854_775_807
  defp uuid?(b), do: is_binary(b) and byte_size(b) == 16
  defp digest?(b), do: is_binary(b) and byte_size(b) == 32

  defp text?(s, n),
    do:
      is_binary(s) and byte_size(s) in 1..n and String.valid?(s) and
        :binary.match(s, <<0>>) == :nomatch

  defp id?(s),
    do:
      text?(s, 128) and
        Enum.all?(
          :binary.bin_to_list(s),
          &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in [?_, ?., ?-])
        )
end
