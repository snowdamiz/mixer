[source, cases_file] = System.argv()
Code.require_file(source)

defmodule IndependentReviewCases do
  def term(%{"bytes" => hex}), do: Base.decode16!(hex, case: :lower)
  def term(%{"repeat" => [byte, size]}), do: :binary.copy(<<byte>>, size)
  def term(%{"atom" => "synthetic"}), do: :synthetic
  def term(%{"tuple" => values}), do: values |> Enum.map(&term/1) |> List.to_tuple()
  def term(%{"bitstring" => 1}), do: <<1::1>>
  def term(%{"bigint" => text}), do: String.to_integer(text)
  def term(%{"improper" => [items, tail]}),
    do: Enum.reduce(Enum.reverse(items), term(tail), fn item, rest -> [term(item) | rest] end)
  def term(:null), do: nil
  def term(items) when is_list(items), do: Enum.map(items, &term/1)
  def term(value), do: value

  def run(cases) do
    Enum.each(cases, fn test ->
      args = term(test["args"])
      expected = case test["expected"] do
        "ok" -> :ok
        "invalid_signature" -> {:error, :invalid_signature}
        "verification_unavailable" -> {:error, :verification_unavailable}
      end
      observed = apply(MixerHosted.Billing.WebhookSignature, :verify, args)
      if observed != expected do
        raise "#{test["category"]}/#{test["name"]}: expected #{inspect(expected)}, got #{inspect(observed)}"
      end
    end)
    IO.puts("PASS: #{length(cases)} independently generated contract cases")
  end
end

payload = cases_file |> File.read!() |> :json.decode()
IndependentReviewCases.run(payload["cases"])
IO.puts(inspect(payload["counts"], limit: :infinity))
