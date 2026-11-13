defmodule MixerHosted.BrowserAuth.ActiveCreate do
  @moduledoc false
  alias MixerHosted.BrowserAuth.{Protocol, RuntimeOwner, ActiveRead}
  alias MixerHosted.Identity.KeyOwner
  @key {__MODULE__, :binding}
  def run(lease, source, identity, _csrf, _headers, {:inputs, input}, nil, key_lease, expires) do
    with_binding(lease, source, identity, key_lease, expires, fn ->
      case MixerHosted.CustomerBuilds.inputs(identity, input) do
        {:ok, value} ->
          {:ok,
           %{
             status: 200,
             headers: [{"cache-control", "no-store"}, {"content-type", "application/json"}],
             body: Jason.encode!(value)
           }}

        error ->
          {:ok, render(error)}
      end
    end)
  end

  def run(lease, source, identity, csrf, headers, input, key, key_lease, expires) do
    if Protocol.verify_csrf(lease.runtime.browser_config, headers, csrf) == :ok do
      with_binding(lease, source, identity, key_lease, expires, fn ->
        {:ok, render(MixerHosted.CustomerBuilds.create(identity, input, key))}
      end)
    else
      {:ok, render({:error, :permission_denied})}
    end
  end

  defp with_binding(lease, source, identity, key_lease, expires, callback) do
    true = is_nil(Process.get(@key))

    true =
      is_map(source.browser) and is_binary(source.browser["cookie_digest"]) and
        byte_size(source.browser["cookie_digest"]) == 32

    Process.put(@key, %{
      owner: self(),
      lease: lease,
      source: source,
      identity: identity,
      key_lease: key_lease,
      expires: expires
    })

    try do
      if lease.runtime.browser_config.scope ==
           "openid mixer.workspace.read mixer.build.read mixer.build.create" and
           "mixer.build.create" in identity.scopes do
        callback.()
      else
        {:ok, render({:error, :permission_denied})}
      end
    after
      Process.delete(@key)
    end
  end

  def require_browser_current!(c) do
    case Process.get(@key) do
      %{owner: owner, identity: identity, source: %{browser: %{"cookie_digest" => digest}}}
      when owner == self() and identity === c.identity and is_binary(digest) and
             byte_size(digest) == 32 ->
        check_current!(c)

      _ ->
        c.repo.rollback(:authorization_unavailable)
    end
  end

  def check_current!(c) do
    case Process.get(@key) do
      nil ->
        :ok

      %{owner: owner, identity: i, lease: l, source: s, key_lease: kl, expires: e}
      when owner == self() and i === c.identity ->
        true =
          System.monotonic_time(:millisecond) < l.deadline and System.system_time(:second) < e

        :ok = RuntimeOwner.checkpoint(l)
        :ok = KeyOwner.finish(KeyOwner, kl)

        [[raw]] =
          MixerHosted.Authorization.Postgres.Session.query!(
            c.repo,
            "SELECT public.mixer_browser_create_active_load($1::bytea,$2::bytea,$3::bigint,ROW($4::text,$5::integer,$6::text,$7::text,$8::text,$9::text,$10::bigint,$11::bigint,$12::text[])::public.mixer_browser_access_evidence)",
            [
              s.browser["cookie_digest"],
              s.browser["config_digest"],
              s.browser["revision"],
              i.profile_id,
              i.profile_version,
              i.issuer,
              i.subject,
              i.client_id,
              i.credential_ref,
              i.issued_at,
              i.expires_at,
              i.scopes
            ]
          ).rows

        ^e = ActiveRead.decode!({:admit, s, i}, raw)
        :ok = KeyOwner.finish(KeyOwner, kl)
        :ok = RuntimeOwner.checkpoint(l)

      _ ->
        c.repo.rollback(:authorization_unavailable)
    end
  end

  def render({:ok, r}) do
    %{
      status: if(r.outcome == :applied, do: 201, else: 200),
      headers: [{"cache-control", "no-store"}, {"content-type", "application/json"}],
      body: Jason.encode!(r)
    }
  end

  def render({:error, reason}) do
    status =
      case reason do
        :invalid_request -> 400
        :unauthenticated -> 401
        :permission_denied -> 403
        :not_found -> 404
        r when r in [:conflict, :idempotency_conflict] -> 409
        _ -> 503
      end

    hs = [{"cache-control", "no-store"}, {"content-type", "application/json"}]

    %{
      status: status,
      headers: if(status == 503, do: [{"retry-after", "1"} | hs], else: hs),
      body: Jason.encode!(%{error: %{code: reason, message: "Build request refused."}})
    }
  end
end

defmodule MixerHosted.BrowserAuth.ActiveCreateSchema do
  @moduledoc false

  def function do
    MixerHosted.BrowserAuth.ActiveReadSchema.function()
    |> String.replace("mixer_browser_current_active_load", "mixer_browser_create_active_load")
    |> String.replace(
      "WHERE id=d.profile_id AND version=d.profile_version FOR UPDATE;",
      "WHERE id=d.profile_id AND version=d.profile_version AND id=i.profile_id AND version=i.profile_version FOR UPDATE;"
    )
  end

  def manifest do
    [_, source, _] = String.split(function(), "$active_read$")

    spec =
      MixerHosted.BrowserAuth.ActiveReadSchema.manifest()
      |> Map.fetch!("mixer_browser_current_active_load")
      |> Map.put(:source, source)

    %{"mixer_browser_create_active_load" => spec}
  end

  def statements do
    [
      function(),
      "REVOKE ALL ON FUNCTION public.mixer_browser_create_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence) FROM PUBLIC"
    ]
  end
end
