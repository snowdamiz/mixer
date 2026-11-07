defmodule ReviewControls do
  alias CallbackFixture, as: F
  alias CallbackFixture.Admin
  alias MixerHosted.BrowserAuth.{CallbackDraft, Protocol, RuntimeOwner, Store, Vault}

  defp assert(value), do: F.assert(value)
  defp hash(value), do: :crypto.hash(:sha256, value)

  defp pending(metadata) do
    {:ok, p} = RuntimeOwner.bootstrap(metadata)
    headers = [{"cookie", "__Host-mixer-session=" <> p.cookie}, {"origin", "https://console.example.invalid"}, {"x-mixer-csrf", p.csrf}]
    {:ok, result} = RuntimeOwner.begin_login(p.cookie, headers, :workspace, metadata)
    state = result.url |> URI.parse() |> Map.fetch!(:query) |> URI.decode_query() |> Map.fetch!("state")
    %{preauth: p, state: state}
  end

  defp discovery(p, lease), do: %CallbackDraft.Discovery{lease: lease, cookie_digest: hash(p.preauth.cookie), state_digest: hash(p.state)}
  defp discover(p) do
    {:ok, lease} = F.lease()
    {:ok, source} = Store.discover_callback(discovery(p, lease))
    {lease, source}
  end

  defp claim(lease, source) do
    e = source.attempt_envelope
    {:ok, %Vault.Verifier{verifier: verifier}} = Vault.open(lease.runtime.custody.key, e.context, e.sealed)
    %CallbackDraft.Claim{lease: lease, source: source, verifier: verifier, claim_secret: :crypto.strong_rand_bytes(32), claim_expires_at: Enum.min([lease.started_at + 60, source.attempt["expires_at"], source.browser["idle_expires_at"], source.browser["absolute_expires_at"]])}
  end

  defp durable do
    %{rows: [[raw]]} = F.sql(Admin, "SELECT jsonb_build_object('browser',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY id),'[]'::jsonb) FROM public.mixer_browser_sessions x),'vault',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id),'[]'::jsonb) FROM public.mixer_browser_session_vault x),'attempt',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY state_digest),'[]'::jsonb) FROM public.mixer_browser_oidc_attempts x),'audit',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id,sequence),'[]'::jsonb) FROM public.mixer_browser_session_events x))")
    raw
  end

  defp invoke(:discovery, draft, _), do: Store.discover_callback(draft)
  defp invoke(:claim, draft, meta), do: Store.claim(draft, meta)
  defp invoke(:reject, draft, meta), do: Store.provider_reject(draft, meta)

  defp captured(fun) do
    try do
      case fun.() do
        {:error, %Store.Failure{phase: :admission, outcome: :not_started}} -> %{closed_failure: true, raised_class: nil}
        _ -> %{closed_failure: false, raised_class: nil}
      end
    rescue
      error -> %{closed_failure: false, raised_class: Atom.to_string(error.__struct__)}
    catch
      kind, _ -> %{closed_failure: false, raised_class: Atom.to_string(kind)}
    end
  end

  def run(_runtime, metadata, _identity_pid) do
    checks = for operation <- [:discovery, :claim, :reject] do
      p = pending(metadata)
      {first_lease, source} = discover(p)
      F.release(first_lease)
      keys = case operation do
        :discovery -> [:lease, :cookie_digest, :state_digest]
        :claim -> [:lease, :source, :verifier, :claim_secret, :claim_expires_at]
        :reject -> [:lease, :source]
      end
      cases = for key <- keys do
        {:ok, lease} = F.lease()
        draft = case operation do
          :discovery -> discovery(p, lease)
          :claim -> claim(lease, source)
          :reject -> %CallbackDraft.Reject{lease: lease, source: source}
        end
        before = durable()
        outcome = captured(fn -> invoke(operation, Map.delete(draft, key), metadata) end)
        unchanged = durable() === before
        guard_restored = Process.get({Store, :callback_active}) === nil
        slot_retained = Map.has_key?(:sys.get_state(lease.owner).operations, lease.reference)
        assert(unchanged and guard_restored)
        if slot_retained, do: F.release(lease)
        Map.merge(outcome, %{missing_key: Atom.to_string(key), durable_unchanged: unchanged, active_guard_restored: guard_restored, original_slot_retained_before_explicit_review_release: slot_retained})
      end
      %{name: "required keys closed for " <> Atom.to_string(operation), invariant_passed: Enum.all?(cases, & &1.closed_failure), cases: cases}
    end

    terminal = for operation <- [:claim, :reject] do
      p = pending(metadata)
      {lease, source} = discover(p)
      wall_key = {Store, :callback_walls}
      assert(Map.has_key?(Process.get(wall_key), lease.reference))
      draft = if operation === :claim, do: claim(lease, source), else: %CallbackDraft.Reject{lease: lease, source: source}
      {:ok, _} = invoke(operation, draft, metadata)
      cleared = not Map.has_key?(Process.get(wall_key), lease.reference)
      guard_restored = Process.get({Store, :callback_active}) === nil
      retained = RuntimeOwner.checkpoint(lease) === :ok
      assert(cleared and guard_restored and retained)
      F.release(lease)
      %{name: "terminal success clears exact local wall and guard for " <> Atom.to_string(operation), invariant_passed: true, original_slot_retained: retained, local_wall_cleared: cleared, active_guard_restored: guard_restored}
    end

    plain = for operation <- [:discovery, :claim, :reject] do
      outcome = captured(fn -> invoke(operation, %{__struct__: case operation do :discovery -> CallbackDraft.Discovery; :claim -> CallbackDraft.Claim; :reject -> CallbackDraft.Reject end}, metadata) end)
      Map.merge(outcome, %{operation: Atom.to_string(operation)})
    end
    checks = checks ++ terminal ++ [%{name: "struct tag alone returns closed failure", invariant_passed: Enum.all?(plain, & &1.closed_failure), cases: plain}]
    File.write!(Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "review-checks.json"), Jason.encode!(checks, pretty: true))
    IO.puts(Jason.encode!(%{review_methods: length(checks), passed_invariants: Enum.count(checks, & &1.invariant_passed), failed_invariants: Enum.count(checks, &(not &1.invariant_passed))}))
  end
end
