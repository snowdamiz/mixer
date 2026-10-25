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
  alias MixerHosted.BrowserAuth.{PreauthDraft, Protocol, RuntimeConfig, Store, Vault}
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

  # These are closed internal owner messages. Actual GenServer caller identity
  # and exact retained lease equality are checked; no supplied PID is authority.
  @doc false
  def checkpoint(%PreauthDraft.Lease{} = lease), do: call(lease, {:checkpoint, lease})
  def checkpoint(_), do: Store.failure(:admission, :not_started)

  defp reserve(deadline, wall),
    do: GenServer.call(__MODULE__, {:reserve, deadline, wall}, remaining(deadline))

  defp execute(lease, operation) do
    # Only the two fixed private orchestration functions create this closure;
    # no exported function accepts caller code or runs provider I/O.
    try do
      result =
        try do
          operation.()
        rescue
          _ -> Store.failure(:effect, :unknown)
        catch
          _, _ -> Store.failure(:commit, :unknown)
        end

      if match?({:error, %Store.Failure{}}, result), do: call(lease, {:failed, lease, result})
      result
    after
      # Release authority comes from GenServer's actual caller, never a PID in
      # a cast. Completed/expired/lost owners are harmless here. After expiry the
      # owner timer supplies cleanup without extending the original deadline.
      if System.monotonic_time(:millisecond) < lease.deadline,
        do: call(lease, {:release, lease})
    end
  end

  defp finish_result(lease, _cookie, {:ok, nil}) do
    with :ok <- call(lease, {:finish, lease, nil}), do: {:ok, nil}
  end

  defp finish_result(lease, cookie, {:ok, snapshot}) do
    # Store has returned a confirmed COMMIT before any decryption occurs here.
    envelope = snapshot.session_envelope
    expires_at = min(snapshot.browser["idle_expires_at"], snapshot.browser["absolute_expires_at"])

    with :preauth <- envelope.context.purpose,
         {:ok, %Vault.Preauth{csrf: csrf}} <-
           Vault.open(lease.runtime.custody.key, envelope.context, envelope.sealed) do
      case call(lease, {:finish, lease, expires_at}) do
        :ok ->
          {:ok,
           %PreauthDraft.Preauth{
             cookie: cookie,
             csrf: csrf,
             expires_at: expires_at,
             source: snapshot
           }}

        {:error, %Store.Failure{}} = error ->
          error

        _ ->
          Store.failure(:commit, :committed)
      end
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

    valid =
      current_lease and
        (is_nil(expires) or (is_integer(expires) and System.system_time(:second) < expires))

    reply = if valid, do: :ok, else: Store.failure(:commit, :committed)
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
