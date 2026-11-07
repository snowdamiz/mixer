defmodule MixerHosted.Identity.HTTPFreshness do
  @moduledoc false
  def calculate(headers, {request_wall, request_mono}, {response_wall, response_mono}) do
    with true <-
           is_integer(request_wall) and is_integer(response_wall) and
             response_mono >= request_mono,
         true <- abs(response_wall - request_wall - (response_mono - request_mono)) <= 1_000,
         {:ok, date} <- date(headers["date"]),
         true <- date * 1_000 <= response_wall + 30_000,
         {:ok, age} <- age(headers["age"]),
         {:ok, lifetime} <- lifetime(headers, date),
         delay = response_mono - request_mono,
         corrected = max(max(0, response_wall - date * 1_000), age * 1_000 + delay),
         remaining = div(min(300_000, lifetime * 1_000 - corrected), 1_000),
         true <- remaining >= 1,
         fetched = div(response_wall, 1_000) do
      {:ok,
       %{
         fetched_at: fetched,
         fresh_until: fetched + remaining,
         expires_mono: response_mono + remaining * 1_000
       }}
    else
      _ -> {:error, :freshness_rejected}
    end
  end

  defp lifetime(h, date) do
    with {:ok, directives} <- directives(h["cache-control"]),
         false <- Map.has_key?(directives, "no-store") or Map.has_key?(directives, "no-cache"),
         true <- h["vary"] in [nil, ""],
         {:ok, maxage} <- optional_seconds(directives["max-age"]),
         {:ok, smax} <- optional_seconds(directives["s-maxage"]),
         {:ok, expires} <- optional_date(h["expires"]),
         limits = Enum.reject([maxage, smax, if(expires, do: expires - date)], &is_nil/1),
         true <-
           (maxage != nil or expires != nil) and limits != [] and Enum.all?(limits, &(&1 > 0)) do
      {:ok, Enum.min(limits)}
    else
      _ -> :error
    end
  end

  defp directives(nil), do: {:ok, %{}}

  defp directives(value) do
    value
    |> String.split(",")
    |> Enum.reduce_while({:ok, %{}}, fn part, {:ok, acc} ->
      case String.split(String.trim(part), "=", parts: 2) do
        [key] -> directive(acc, key, true)
        [key, value] -> directive(acc, key, value)
      end
    end)
  end

  defp directive(acc, key, value) do
    key = String.downcase(key)

    valid =
      Regex.match?(~r/^[!#$%&'*+.^_`|~0-9a-z-]+$/, key) and
        (value == true or
           Regex.match?(~r/^(?:[!#$%&'*+.^_`|~0-9A-Za-z-]+|"[^"\\\x00-\x1f]*")$/, value))

    if valid and not Map.has_key?(acc, key),
      do: {:cont, {:ok, Map.put(acc, key, value)}},
      else: {:halt, :error}
  end

  defp optional_seconds(nil), do: {:ok, nil}
  defp optional_seconds(s), do: age(s)
  defp age(nil), do: {:ok, 0}

  defp age(s) when is_binary(s) and byte_size(s) <= 10 do
    if Regex.match?(~r/^[0-9]+$/, s) do
      n = String.to_integer(s)
      if n <= 2_147_483_647, do: {:ok, n}, else: :error
    else
      :error
    end
  end

  defp age(_), do: :error
  defp optional_date(nil), do: {:ok, nil}
  defp optional_date(s), do: date(s)

  defp date(s) when is_binary(s) and byte_size(s) == 29 do
    case :httpd_util.convert_request_date(String.to_charlist(s)) do
      {{y, m, d}, {h, min, sec}} = dt when y >= 1970 and sec in 0..59 ->
        if :calendar.valid_date({y, m, d}) and h in 0..23 and min in 0..59 and
             Calendar.strftime(NaiveDateTime.from_erl!(dt), "%a, %d %b %Y %H:%M:%S GMT") == s,
           do: {:ok, :calendar.datetime_to_gregorian_seconds(dt) - 62_167_219_200},
           else: :error

      _ ->
        :error
    end
  rescue
    _ -> :error
  end

  defp date(_), do: :error
end
