defmodule MixerHosted.BrowserAuth.RuntimeOwner do
  @moduledoc """
  Manually supervised, fixed preauthentication owner. No Application wiring yet.

  Storage readiness requires both current catalogs on the dedicated pool. It is
  never browser authentication readiness. Startup receives trusted configuration;
  this component cannot attest that a future Application used the same loader.
  Private preauthentication values must never be logged or serialized to HTTP.
  """
  use GenServer
  alias MixerHosted.BrowserAuth.{ConfigurationDigest, Custody, LifecycleRepo}

  alias MixerHosted.BrowserAuth.{
    PreauthDraft,
    Protocol,
    RuntimeConfig,
    Store,
    StoredSnapshot,
    Vault
  }

  alias MixerHosted.Identity.KeyOwner

  def start_link(%RuntimeConfig{} = runtime),
    do: GenServer.start_link(__MODULE__, runtime, name: __MODULE__)

  def status do
    GenServer.call(__MODULE__, :status, 1000)
  catch
    :exit, _ -> %{phase: :unavailable, generation: 0}
  end

  @doc "Creates private preauthentication data only; no authenticated session or HTTP cookie is installed."
  def bootstrap(metadata) do
    deadline = System.monotonic_time(:millisecond) + 5000
    wall = System.system_time(:second)

    with true <- metadata?(metadata),
         {:ok, lease} <- reserve(deadline, wall) do
      execute(lease, fn ->
        cookie = Protocol.random_token()
        csrf = Protocol.random_token()
        runtime = lease.runtime
        config = runtime.browser_config

        context = %{
          purpose: :preauth,
          browser_id: :crypto.strong_rand_bytes(16),
          cookie_digest: :crypto.hash(:sha256, cookie),
          csrf_digest: :crypto.hash(:sha256, csrf),
          epoch: 1,
          revision: 1,
          generation: Protocol.random_token(),
          vault_generation: 1,
          config_digest: runtime.configuration_digest,
          profile_id: config.profile_id,
          profile_version: config.profile_version,
          principal_id: nil,
          family_id: nil,
          credential_ref: nil,
          credential_revision: nil
        }

        with {:ok, sealed} <- Vault.seal(runtime.custody.key, context, %Vault.Preauth{csrf: csrf}) do
          draft = %PreauthDraft.Bootstrap{
            lease: lease,
            context: context,
            sealed: sealed,
            cookie: cookie,
            csrf: csrf,
            expires_at: wall + 300
          }

          finish_result(lease, cookie, Store.bootstrap(draft, metadata))
        else
          _ -> Store.failure(:effect, :not_started)
        end
      end)
    else
      _ -> Store.failure(:admission, :not_started)
    end
  rescue
    _ -> Store.failure(:admission, :not_started)
  catch
    _, _ -> Store.failure(:admission, :not_started)
  end

  def load(cookie) do
    deadline = System.monotonic_time(:millisecond) + 5000
    wall = System.system_time(:second)

    with true <- Protocol.token?(cookie),
         {:ok, lease} <- reserve(deadline, wall) do
      execute(lease, fn ->
        input = %PreauthDraft.Load{lease: lease, cookie_digest: :crypto.hash(:sha256, cookie)}
        finish_result(lease, cookie, Store.load(input))
      end)
    else
      _ -> Store.failure(:admission, :not_started)
    end
  rescue
    _ -> Store.failure(:admission, :not_started)
  catch
    _, _ -> Store.failure(:admission, :not_started)
  end

  @doc "Begins only a private preauthentication OIDC attempt; no route or authenticated session is installed."
  def begin_login(cookie, raw_headers, return_route, metadata) do
    deadline = System.monotonic_time(:millisecond) + 5000
    wall = System.system_time(:second)

    with true <- metadata?(metadata) and return_route === :workspace and Protocol.token?(cookie),
         {:ok, ^cookie} <- Protocol.parse_session_cookie(raw_headers),
         {:ok, lease} <- reserve(deadline, wall) do
      execute(lease, fn ->
        input = %PreauthDraft.Load{lease: lease, cookie_digest: :crypto.hash(:sha256, cookie)}

        with {:ok, %StoredSnapshot{} = source} <- Store.discover_begin(input),
             {:ok, draft} <- prepare_begin(lease, raw_headers, source),
             {:ok, _snapshot} <- Store.begin_login(draft, metadata) do
          finish_receipt(lease, draft.attempt_context.expires_at, %PreauthDraft.Authorization{
            url: draft.url,
            expires_at: draft.attempt_context.expires_at
          })
        else
          {:error, %Store.Failure{}} = error -> error
          _ -> Store.failure(:decode, :committed)
        end
      end)
    else
      _ -> Store.failure(:admission, :not_started)
    end
  rescue
    _ -> Store.failure(:admission, :not_started)
  catch
    _, _ -> Store.failure(:admission, :not_started)
  end

  defp prepare_begin(lease, raw_headers, source) do
    runtime = lease.runtime
    config = runtime.browser_config
    envelope = source.session_envelope

    expires =
      min(
        lease.started_at + 300,
        min(source.browser["idle_expires_at"], source.browser["absolute_expires_at"])
      )

    with :ok <- checkpoint(lease),
         :preauth <- envelope.context.purpose,
         {:ok, %Vault.Preauth{csrf: csrf}} <-
           Vault.open(runtime.custody.key, envelope.context, envelope.sealed),
         :ok <- Protocol.verify_csrf(config, raw_headers, csrf),
         true <- System.system_time(:second) < expires do
      state = Protocol.random_token()
      nonce = Protocol.random_token()
      verifier = Protocol.random_token()
      c = envelope.context

      context = %{
        c
        | epoch: c.epoch + 1,
          revision: c.revision + 1,
          vault_generation: c.vault_generation + 1
      }

      attempt = %{
        purpose: :attempt,
        state_digest: :crypto.hash(:sha256, state),
        browser_id: context.browser_id,
        cookie_digest: context.cookie_digest,
        epoch: context.epoch,
        revision: context.revision,
        generation: context.generation,
        config_digest: runtime.configuration_digest,
        profile_id: config.profile_id,
        profile_version: config.profile_version,
        issuer: config.issuer,
        client_id: config.client_id,
        redirect_uri: config.redirect_uri,
        expires_at: expires
      }

      with {:ok, url} <-
             Protocol.authorization_url(config, %{state: state, nonce: nonce, verifier: verifier}),
           true <- byte_size(url) <= 8192,
           {:ok, sealed} <- Vault.seal(runtime.custody.key, context, %Vault.Preauth{csrf: csrf}),
           {:ok, attempt_sealed} <-
             Vault.seal(runtime.custody.key, attempt, %Vault.Verifier{verifier: verifier}),
           :ok <- checkpoint(lease) do
        {:ok,
         %PreauthDraft.Begin{
           lease: lease,
           source: source,
           context: context,
           sealed: sealed,
           attempt_context: attempt,
           attempt_sealed: attempt_sealed,
           state: state,
           nonce: nonce,
           verifier: verifier,
           csrf: csrf,
           url: url
         }}
      else
        {:error, %Store.Failure{}} = error -> error
        _ -> Store.failure(:effect, :not_started)
      end
    else
      {:error, %Store.Failure{}} = error -> error
      _ -> Store.failure(:decode, :committed)
    end
  end

  # These are closed internal owner messages. Actual GenServer caller identity
  # and exact retained lease equality are checked; no supplied PID is authority.
  @doc false
  def checkpoint(%PreauthDraft.Lease{} = lease), do: call(lease, {:checkpoint, lease})
  def checkpoint(_), do: Store.failure(:admission, :not_started)

  defp reserve(deadline, wall),
    do: GenServer.call(__MODULE__, {:reserve, deadline, wall}, remaining(deadline))

  defp execute(lease, operation) do
    # Only the fixed private orchestration functions create this closure;
    # no exported function accepts caller code or runs provider I/O.
    result =
      try do
        operation.()
      rescue
        _ -> Store.failure(:effect, :unknown)
      catch
        _, _ -> Store.failure(:commit, :unknown)
      end

    case result do
      %PreauthDraft.Publication{} = receipt ->
        # Finish already released the exact retained caller permit. No external
        # cleanup call may delay a successful value after this final sample.
        publish(lease, receipt)

      error ->
        if match?({:error, %Store.Failure{}}, error), do: call(lease, {:failed, lease, error})

        # Caller-authorized fallback only. Expiry/monitors clean up after the
        # unchanged deadline. A completed finish needs no second release.
        if System.monotonic_time(:millisecond) < lease.deadline,
          do: call(lease, {:release, lease})

        error
    end
  end

  defp finish_receipt(lease, expires, value) do
    case call(lease, {:finish, lease, expires}) do
      {:ok, checked_wall} when is_integer(checked_wall) ->
        %PreauthDraft.Publication{checked_wall: checked_wall, expires_at: expires, value: value}

      _ ->
        Store.failure(:commit, :committed)
    end
  rescue
    _ -> Store.failure(:commit, :committed)
  catch
    _, _ -> Store.failure(:commit, :committed)
  end

  defp publish(lease, receipt) do
    # The retained PID/status samples current dependency/configuration binding;
    # neither a registered replacement nor a new timeout can authorize release.
    with true <- System.monotonic_time(:millisecond) < lease.deadline,
         %{phase: :storage_ready, generation: generation} <- call(lease, :status),
         true <- generation === lease.generation,
         wall = System.system_time(:second),
         true <- wall >= receipt.checked_wall,
         true <- is_nil(receipt.expires_at) or wall < receipt.expires_at,
         true <- System.monotonic_time(:millisecond) < lease.deadline,
         true <- Process.whereis(__MODULE__) === lease.owner do
      {:ok, receipt.value}
    else
      _ -> Store.failure(:commit, :committed)
    end
  rescue
    _ -> Store.failure(:commit, :committed)
  catch
    _, _ -> Store.failure(:commit, :committed)
  end

  defp finish_result(lease, _cookie, {:ok, nil}) do
    finish_receipt(lease, nil, nil)
  end

  defp finish_result(lease, cookie, {:ok, snapshot}) do
    # Store has returned a confirmed COMMIT before any decryption occurs here.
    envelope = snapshot.session_envelope
    expires_at = min(snapshot.browser["idle_expires_at"], snapshot.browser["absolute_expires_at"])

    with :preauth <- envelope.context.purpose,
         {:ok, %Vault.Preauth{csrf: csrf}} <-
           Vault.open(lease.runtime.custody.key, envelope.context, envelope.sealed) do
      finish_receipt(lease, expires_at, %PreauthDraft.Preauth{
        cookie: cookie,
        csrf: csrf,
        expires_at: expires_at,
        source: snapshot
      })
    else
      _ -> Store.failure(:decode, :committed)
    end
  end

  defp finish_result(_lease, _cookie, error), do: error

  defp call(lease, message) do
    if Process.whereis(__MODULE__) === lease.owner,
      do: GenServer.call(lease.owner, message, remaining(lease.deadline)),
      else: Store.failure(:commit, :committed)
  catch
    :exit, _ -> Store.failure(:commit, :committed)
  end

  @impl true
  def init(%RuntimeConfig{mode: :disabled} = runtime) do
    if Enum.all?(
         [
           runtime.browser_config,
           runtime.configuration_digest,
           runtime.lifecycle_repo,
           runtime.expected_roles,
           runtime.custody
         ],
         &is_nil/1
       ),
       do: {:ok, %{phase: :disabled, generation: 0, operations: %{}, monitors: %{}}},
       else: {:stop, :session_unavailable}
  end

  def init(%RuntimeConfig{mode: :configured} = runtime) do
    deadline = System.monotonic_time(:millisecond) + 5000

    with :ok <- validate_runtime(runtime),
         repo when is_pid(repo) <- Process.whereis(LifecycleRepo),
         identity when is_pid(identity) <- Process.whereis(KeyOwner),
         ordinary when is_pid(ordinary) <- Process.whereis(MixerHosted.Repo) do
      monitors = Map.new([repo, identity, ordinary], &{Process.monitor(&1), &1})

      phase =
        if Store.admit(runtime, deadline) === {:ok, :admitted},
          do: :storage_ready,
          else: :unavailable

      {:ok,
       %{
         phase: phase,
         generation: 1,
         runtime: runtime,
         repo: repo,
         identity: identity,
         ordinary: ordinary,
         operations: %{},
         monitors: monitors
       }}
    else
      _ -> {:stop, :session_unavailable}
    end
  end

  @impl true
  def format_status(status) do
    Map.new(status, fn
      {:state, state} -> {:state, Map.take(state, [:phase, :generation])}
      {key, _} when key in [:message, :reason, :log] -> {key, :redacted}
      pair -> pair
    end)
  end

  @impl true
  def handle_call(:status, _from, state) do
    state = current(state)
    {:reply, Map.take(state, [:phase, :generation]), state}
  end

  def handle_call({:reserve, deadline, wall}, {caller, _}, state) do
    state = current(state)

    if state.phase === :storage_ready and map_size(state.operations) < 32 and
         valid_time?(deadline, wall) do
      ref = make_ref()

      lease = %PreauthDraft.Lease{
        owner: self(),
        reference: ref,
        caller: caller,
        generation: state.generation,
        deadline: deadline,
        started_at: wall,
        runtime: state.runtime
      }

      monitor = Process.monitor(caller)
      expiry = make_ref()
      timer = Process.send_after(self(), {:expire, ref, expiry}, remaining(deadline))

      operations =
        Map.put(state.operations, ref, %{
          lease: lease,
          monitor: monitor,
          timer: timer,
          expiry: expiry,
          last_wall: wall
        })

      {:reply, {:ok, lease}, %{state | operations: operations}}
    else
      {:reply, Store.failure(:admission, :not_started), state}
    end
  end

  def handle_call({:checkpoint, lease}, {caller, _}, state) do
    state = current(state)
    {valid, state} = sample_lease(state, lease, caller)

    reply =
      if valid, do: :ok, else: Store.failure(:commit, :committed)

    {:reply, reply, state}
  end

  def handle_call({:finish, lease, expires}, {caller, _}, state) do
    state = current(state)
    {current_lease, state} = sample_lease(state, lease, caller)
    checked_wall = if current_lease, do: state.operations[lease.reference].last_wall

    valid =
      current_lease and
        (is_nil(expires) or (is_integer(expires) and checked_wall < expires))

    reply =
      if valid,
        do: {:ok, checked_wall},
        else: Store.failure(:commit, :committed)

    state = if valid, do: release(state, lease.reference), else: state
    {:reply, reply, state}
  end

  def handle_call({:failed, lease, {:error, %Store.Failure{} = error}}, {caller, _}, state) do
    if owned_lease?(state, lease, caller) and failure?(error) do
      state =
        if (error.phase === :admission and error.outcome !== :not_started) or
             error.outcome === :unknown, do: invalidate(state), else: state

      {:reply, :ok, release(state, lease.reference)}
    else
      {:reply, Store.failure(:admission, :not_started), state}
    end
  end

  def handle_call({:release, lease}, {caller, _}, state) do
    if owned_lease?(state, lease, caller),
      do: {:reply, :ok, release(state, lease.reference)},
      else: {:reply, Store.failure(:admission, :not_started), state}
  end

  def handle_call(_, _from, state), do: {:reply, Store.failure(:admission, :not_started), state}

  @impl true
  def handle_cast(_, state), do: {:noreply, state}

  @impl true
  def handle_info({:DOWN, monitor, :process, _pid, _reason}, state) do
    if Map.has_key?(state.monitors, monitor) do
      {:noreply, invalidate(state)}
    else
      reference =
        Enum.find_value(state.operations, fn {ref, operation} ->
          if operation.monitor === monitor, do: ref
        end)

      {:noreply, release(state, reference)}
    end
  end

  def handle_info({:expire, reference, expiry}, state) do
    # An expired operation may be waiting for COMMIT acknowledgement. Releasing
    # its slot cannot preserve readiness on an outcome we can no longer fence.
    state =
      case Map.get(state.operations, reference) do
        %{expiry: ^expiry} -> invalidate(state)
        _ -> state
      end

    {:noreply, state}
  end

  def handle_info(_, state), do: {:noreply, state}

  defp current(%{phase: :storage_ready} = state) do
    if Process.whereis(LifecycleRepo) === state.repo and
         Process.whereis(KeyOwner) === state.identity and
         Process.whereis(MixerHosted.Repo) === state.ordinary and repo_bound?(state.runtime),
       do: state,
       else: invalidate(state)
  end

  defp current(state), do: state

  defp invalidate(%{phase: :disabled} = state), do: state

  defp invalidate(state) do
    state = Enum.reduce(Map.keys(state.operations), state, &release(&2, &1))
    %{state | phase: :unavailable, generation: state.generation + 1}
  end

  defp owned_lease?(state, %PreauthDraft.Lease{} = lease, caller) do
    case Map.get(state.operations, lease.reference) do
      %{lease: ^lease} -> lease.caller === caller and lease.owner === self()
      _ -> false
    end
  end

  defp owned_lease?(_, _, _), do: false

  defp failure?(
         %Store.Failure{code: :session_unavailable, phase: phase, outcome: outcome} = error
       ),
       do:
         map_size(error) == 4 and phase in [:admission, :effect, :decode, :commit] and
           outcome in [:not_started, :rolled_back, :committed, :unknown]

  defp failure?(_), do: false

  defp valid_lease?(state, lease, caller),
    do:
      state.phase === :storage_ready and
        owned_lease?(state, lease, caller) and lease.generation === state.generation and
        valid_time?(lease.deadline, lease.started_at)

  defp sample_lease(state, lease, caller) do
    if valid_lease?(state, lease, caller) do
      operation = Map.fetch!(state.operations, lease.reference)
      wall = System.system_time(:second)

      if wall >= operation.last_wall do
        operations = Map.put(state.operations, lease.reference, %{operation | last_wall: wall})
        {true, %{state | operations: operations}}
      else
        {false, invalidate(state)}
      end
    else
      {false, state}
    end
  end

  defp release(state, reference) do
    case Map.pop(state.operations, reference) do
      {nil, _} ->
        state

      {%{monitor: monitor, timer: timer}, operations} ->
        Process.demonitor(monitor, [:flush])
        Process.cancel_timer(timer)
        %{state | operations: operations}
    end
  end

  defp validate_runtime(runtime) do
    with true <- map_size(runtime) == 7,
         {:ok, digest} <- ConfigurationDigest.digest(runtime.browser_config),
         true <- digest === runtime.configuration_digest,
         %Custody{reference: reference, key: key} <- runtime.custody,
         true <- reference === runtime.browser_config.session_vault_ref,
         {:ok, custody} <-
           Custody.new(reference, %{reference: reference, key_id: key.id, key_bytes: key.bytes}),
         true <- custody === runtime.custody,
         true <- repo_bound?(runtime),
         true <-
           MixerHosted.Repo.config()[:username] === runtime.expected_roles.ordinary_runtime_login do
      :ok
    else
      _ -> :error
    end
  rescue
    _ -> :error
  end

  defp repo_bound?(runtime) do
    runtime.lifecycle_repo[:pool_size] === 2 and runtime.lifecycle_repo[:pool_count] === 1 and
      runtime.lifecycle_repo[:queue] === false and runtime.lifecycle_repo[:timeout] === 5000 and
      runtime.lifecycle_repo[:connect_timeout] === 5000 and
      runtime.lifecycle_repo[:show_sensitive_data_on_connection_error] === false and
      runtime.lifecycle_repo[:username] === runtime.expected_roles.lifecycle_login and
      LifecycleRepo.bound?(runtime.lifecycle_repo)
  rescue
    _ -> false
  end

  defp valid_time?(deadline, wall),
    do:
      is_integer(deadline) and is_integer(wall) and
        System.monotonic_time(:millisecond) < deadline and
        deadline <= System.monotonic_time(:millisecond) + 5000 and
        System.system_time(:second) >= wall

  defp remaining(deadline), do: max(1, min(5000, deadline - System.monotonic_time(:millisecond)))

  defp metadata?(%{request_id: id} = metadata)
       when map_size(metadata) == 1 and is_binary(id) and byte_size(id) == 32,
       do: Enum.all?(:binary.bin_to_list(id), &(&1 in ?0..?9 or &1 in ?a..?f))

  defp metadata?(_), do: false
end
