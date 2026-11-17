defmodule MixerHosted.Billing.Entitlements do
  @moduledoc false
  alias MixerHosted.Billing.ObservedSubscription
  @spec decide(ObservedSubscription.t()) :: {:blocked, :ordering_unavailable}
  def decide(%ObservedSubscription{ordering: :ordering_unavailable}),
    do: {:blocked, :ordering_unavailable}
end
