defmodule MixerHosted.Identity.Encoding do
  @moduledoc false
  @max_integer 9_007_199_254_740_991

  def bounded_string?(value, limit) do
    is_binary(value) and byte_size(value) in 1..limit and String.valid?(value)
  end

  def numeric_date?(value), do: is_integer(value) and value >= 0 and value <= @max_integer

  def decode64(segment, limit)
      when is_binary(segment) and byte_size(segment) > 0 and
             byte_size(segment) <= div(limit * 4 + 2, 3) do
    with {:ok, value} <- Base.url_decode64(segment, padding: false),
         true <- byte_size(value) <= limit,
         ^segment <- Base.url_encode64(value, padding: false) do
      {:ok, value}
    else
      _ -> :error
    end
  end

  def decode64(_, _), do: :error
end
