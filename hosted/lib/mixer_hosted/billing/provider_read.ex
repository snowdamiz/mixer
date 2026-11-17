defmodule MixerHosted.Billing.ProviderRead do
  @moduledoc false
  alias MixerHosted.Billing.{Bindings.Target, SubscriptionReadTransport}

  defmodule Observation do
    @moduledoc false
    @enforce_keys [:target, :value, :response_sha256]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  @spec fetch(Target.t()) :: {:ok, Observation.t()} | {:error, atom()}
  def fetch(%Target{} = target) do
    with %{enabled: true, profile: :billing_v1, transport: config, secret_resolver: resolver} <-
           Application.get_env(:mixer_hosted, :billing_processor),
         {:ok, handle} <-
           SubscriptionReadTransport.new(
             Map.merge(config, %{
               account: target.account,
               livemode: target.livemode,
               secret_ref: target.secret_ref
             }),
             resolver
           ),
         {:ok, {value, digest}} <- read(handle, target) do
      {:ok, %Observation{target: target, value: value, response_sha256: digest}}
    else
      _ -> {:error, :provider_unavailable}
    end
  end

  if Mix.env() == :test do
    defp read(handle, target) do
      case Application.get_env(:mixer_hosted, :billing_test_destination) do
        {{127, 0, 0, 1}, port} ->
          SubscriptionReadTransport.read_checked_fixture(
            handle,
            target.subscription_id,
            target.customer_id,
            {127, 0, 0, 1},
            port
          )

        nil ->
          SubscriptionReadTransport.read_checked(
            handle,
            target.subscription_id,
            target.customer_id
          )
      end
    end
  else
    defp read(handle, target),
      do:
        SubscriptionReadTransport.read_checked(handle, target.subscription_id, target.customer_id)
  end
end
