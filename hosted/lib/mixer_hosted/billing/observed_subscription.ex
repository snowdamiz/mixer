defmodule MixerHosted.Billing.ObservedSubscription do
  @moduledoc """
  Private checked read observation, deliberately lacking provider ordering and
  owning-account proof. This is not an ordered ReadOnlyProvider snapshot.
  """
  alias MixerHosted.Identity.BoundedJSON

  @enforce_keys [:subscription_id, :customer_id, :livemode, :status]
  defstruct @enforce_keys ++ [ordering: :ordering_unavailable]

  @opaque t :: %__MODULE__{
            subscription_id: binary(),
            customer_id: binary(),
            livemode: boolean(),
            status: binary(),
            ordering: :ordering_unavailable
          }
  @statuses ~w(incomplete incomplete_expired trialing active past_due canceled unpaid paused)

  def id?(value, prefix) when is_binary(value) and byte_size(value) <= 128,
    do:
      String.starts_with?(value, prefix) and
        Regex.match?(
          ~r/\A[A-Za-z0-9]+\z/,
          binary_part(value, byte_size(prefix), byte_size(value) - byte_size(prefix))
        )

  def id?(_, _), do: false

  @spec decode(binary(), binary(), binary(), boolean()) :: {:ok, t()} | {:error, atom()}
  def decode(raw, subscription, customer, mode) do
    with true <- id?(subscription, "sub_") and id?(customer, "cus_") and is_boolean(mode),
         true <- is_binary(raw) and byte_size(raw) <= 262_144,
         true <- depth?(raw, 0, false, false),
         {:ok, obj} <- BoundedJSON.object(raw, 262_144),
         %{
           "object" => "subscription",
           "id" => ^subscription,
           "customer" => ^customer,
           "livemode" => ^mode,
           "status" => status
         } <- obj,
         true <- status in @statuses do
      {:ok,
       %__MODULE__{
         subscription_id: subscription,
         customer_id: customer,
         livemode: mode,
         status: status
       }}
    else
      _ -> {:error, :observation_rejected}
    end
  rescue
    _ -> {:error, :observation_rejected}
  end

  # Bound nesting before the general JSON decoder allocates a tree. The decoder
  # still owns syntax/UTF-8/duplicate-key validation, including ignored fields.
  defp depth?(_, n, _, _) when n > 16 or n < 0, do: false
  defp depth?(<<>>, 0, false, false), do: true
  defp depth?(<<>>, _, _, _), do: false
  defp depth?(<<_, rest::binary>>, n, true, true), do: depth?(rest, n, true, false)
  defp depth?(<<?\\, rest::binary>>, n, true, false), do: depth?(rest, n, true, true)
  defp depth?(<<?", rest::binary>>, n, quoted, false), do: depth?(rest, n, not quoted, false)

  defp depth?(<<c, rest::binary>>, n, false, false) when c in [?{, ?[],
    do: depth?(rest, n + 1, false, false)

  defp depth?(<<c, rest::binary>>, n, false, false) when c in [?}, ?]],
    do: depth?(rest, n - 1, false, false)

  defp depth?(<<_, rest::binary>>, n, quoted, escaped), do: depth?(rest, n, quoted, escaped)
end
