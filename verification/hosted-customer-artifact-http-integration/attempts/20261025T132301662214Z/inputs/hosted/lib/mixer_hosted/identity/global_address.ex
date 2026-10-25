defmodule MixerHosted.Identity.GlobalAddress do
  @moduledoc false
  import Bitwise
  # Conservative reviewed IANA global-unicast allowspace, with special-purpose
  # blocks denied wholesale (including individually global special exceptions).
  @v4 [
    {{0, 0, 0, 0}, 8},
    {{10, 0, 0, 0}, 8},
    {{100, 64, 0, 0}, 10},
    {{127, 0, 0, 0}, 8},
    {{169, 254, 0, 0}, 16},
    {{172, 16, 0, 0}, 12},
    {{192, 0, 0, 0}, 24},
    {{192, 0, 2, 0}, 24},
    {{192, 88, 99, 0}, 24},
    {{192, 168, 0, 0}, 16},
    {{198, 18, 0, 0}, 15},
    {{198, 51, 100, 0}, 24},
    {{203, 0, 113, 0}, 24},
    {{224, 0, 0, 0}, 3}
  ]
  @v6 [
    {{0x2001, 0, 0, 0, 0, 0, 0, 0}, 23},
    {{0x2001, 0xDB8, 0, 0, 0, 0, 0, 0}, 32},
    {{0x2002, 0, 0, 0, 0, 0, 0, 0}, 16},
    {{0x3FFF, 0, 0, 0, 0, 0, 0, 0}, 20}
  ]
  def normalize({0, 0, 0, 0, 0, 0xFFFF, a, b}), do: {a >>> 8, a &&& 255, b >>> 8, b &&& 255}
  def normalize(ip), do: ip

  def global?(ip) do
    ip = normalize(ip)

    case ip do
      {a, b, c, d} when a in 0..255 and b in 0..255 and c in 0..255 and d in 0..255 ->
        not Enum.any?(@v4, fn {base, bits} -> prefix?(ip, base, bits, 32) end)

      {a, b, c, d, e, f, g, h}
      when a in 0..65535 and b in 0..65535 and c in 0..65535 and d in 0..65535 and e in 0..65535 and
             f in 0..65535 and g in 0..65535 and h in 0..65535 ->
        prefix?(ip, {0x2000, 0, 0, 0, 0, 0, 0, 0}, 3, 128) and
          not Enum.any?(@v6, fn {base, bits} -> prefix?(ip, base, bits, 128) end)

      _ ->
        false
    end
  end

  defp prefix?(a, b, bits, total),
    do: number(a) >>> (total - bits) == number(b) >>> (total - bits)

  defp number(ip) do
    shift = if tuple_size(ip) == 4, do: 8, else: 16
    ip |> Tuple.to_list() |> Enum.reduce(0, fn n, acc -> (acc <<< shift) + n end)
  end
end
