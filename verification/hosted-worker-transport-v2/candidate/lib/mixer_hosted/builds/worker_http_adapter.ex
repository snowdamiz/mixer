defmodule MixerHosted.Builds.WorkerHTTPAdapter do
  @moduledoc "Actual authenticated outbound worker adapter; no default installation."
  @behaviour MixerHosted.Builds.Dispatch
  alias MixerHosted.Builds.WorkerTransport
  @impl true
  def query(request), do: WorkerTransport.perform(:query, request)
  @impl true
  def ensure_started(request), do: WorkerTransport.perform(:ensure_started, request)
  @impl true
  def stop(request), do: WorkerTransport.perform(:stop, request)
end
