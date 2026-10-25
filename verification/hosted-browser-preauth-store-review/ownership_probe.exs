Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :error)
Code.require_file("verification/hosted-browser-preauth-store-review/synthetic_runtime_fixture.exs")

alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner, Store}
alias MixerHosted.Identity.KeyOwner

fixture =
  MixerPreauthStoreReview.SyntheticRuntimeFixture.build(
    String.to_integer(System.fetch_env!("PREAUTH_REVIEW_PORT")),
    "review_browser"
  )

Application.put_env(:mixer_hosted, MixerHosted.Repo, fixture.ordinary_repo)
{:ok, ordinary} = MixerHosted.Repo.start_link(fixture.ordinary_repo)
{:ok, lifecycle} = LifecycleRepo.start_link(fixture.runtime.lifecycle_repo)
{:ok, workers} = DynamicSupervisor.start_link(strategy: :one_for_one, name: ReviewFetchWorkers)

roots =
  Enum.map(:public_key.cacerts_get(), fn
    {:cert, der, _} -> der
    der when is_binary(der) -> der
  end)

{:ok, identity} =
  KeyOwner.start_link(
    manifest: fixture.identity_manifest,
    generation: 1,
    binding: fixture.identity_binding,
    ca_roots: roots,
    resolvers: [{{1, 1, 1, 1}, 53}],
    worker_supervisor: ReviewFetchWorkers
  )

{:ok, owner} = RuntimeOwner.start_link(fixture.runtime)
parent = self()
checks = []

try do
  true = RuntimeOwner.status().phase === :storage_ready

  for action <- [:finish, :failed, :spoofed_release_cast] do
    caller =
      spawn(fn ->
        deadline = System.monotonic_time(:millisecond) + 5000
        wall = System.system_time(:second)
        {:ok, lease} = GenServer.call(owner, {:reserve, deadline, wall})
        send(parent, {:reserved, self(), lease})

        receive do
          :checkpoint -> send(parent, {:original_checkpoint, RuntimeOwner.checkpoint(lease)})
        after
          4000 -> :ok
        end
      end)

    lease =
      receive do
        {:reserved, ^caller, lease} -> lease
      after
        2000 -> raise "reservation message missing"
      end

    response =
      case action do
        :finish -> GenServer.call(owner, {:finish, lease, nil})
        :failed -> GenServer.call(owner, {:failed, lease, Store.failure(:effect, :rolled_back)})
        :spoofed_release_cast -> GenServer.cast(owner, {:release, caller, lease.reference})
      end

    retained = Map.has_key?(:sys.get_state(owner).operations, lease.reference)
    send(caller, :checkpoint)

    original_allowed =
      receive do
        {:original_checkpoint, result} -> result === :ok
      after
        2000 -> false
      end

    record = %{
      control: "O03",
      fixed_message: Atom.to_string(action),
      foreign_reply_redacted: response === Store.failure(:commit, :committed) or response === :ok,
      original_lease_retained: retained,
      original_caller_checkpoint_allowed: original_allowed,
      invariant_passed: retained and original_allowed
    }

    Process.put(:review_ownership_checks, Process.get(:review_ownership_checks, checks) ++ [record])
  end
after
  for pid <- [owner, lifecycle, ordinary, identity, workers] do
    if Process.alive?(pid), do: GenServer.stop(pid, :normal, 2000)
  end
end

records = Process.get(:review_ownership_checks, [])
File.write!(Path.join(System.fetch_env!("PREAUTH_REVIEW_OUTPUT"), "checks.json"), Jason.encode!(records, pretty: true))
IO.puts(Jason.encode!(%{ownership_controls: length(records), invariants_passed: Enum.all?(records, & &1.invariant_passed)}))
