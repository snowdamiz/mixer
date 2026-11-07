defmodule MixerHosted.Identity.DNSResolver do
  @moduledoc false
  alias MixerHosted.Identity.GlobalAddress

  def resolve(host, resolvers, deadline) do
    with {:ok, a} <- query(host, :a, resolvers, deadline),
         {:ok, b} <- query(host, :aaaa, resolvers, deadline),
         ips = Enum.uniq(a ++ b),
         true <- length(ips) in 1..16 and Enum.all?(ips, &GlobalAddress.global?/1) do
      {:ok, ips |> Enum.sort() |> hd()}
    else
      _ -> {:error, :dns_rejected}
    end
  rescue
    _ -> {:error, :dns_rejected}
  catch
    _, _ -> {:error, :dns_rejected}
  end

  defp query(host, type, resolvers, deadline) do
    remaining = deadline - System.monotonic_time(:millisecond)

    if remaining <= 0 do
      {:error, :deadline}
    else
      opts = [
        nameservers: resolvers,
        alt_nameservers: [],
        retry: 1,
        timeout: remaining,
        edns: 0,
        udp_payload_size: 1232,
        usevc: false
      ]

      case :inet_res.resolve(String.to_charlist(host <> "."), :in, type, opts, remaining) do
        {:ok, msg} -> validate(msg, host, type)
        _ -> {:error, :dns_rejected}
      end
    end
  end

  defp validate(msg, host, type) do
    header = :inet_dns.msg(msg, :header)
    answers = :inet_dns.msg(msg, :anlist)

    with false <- :inet_dns.header(header, :tc),
         true <- byte_size(:inet_dns.encode(msg)) <= 65_536,
         true <- length(answers) <= 32,
         true <- Enum.all?(answers, &(:inet_dns.rr(&1, :class) == :in)),
         {:ok, ips} <- chain(host, type, answers, MapSet.new(), 0) do
      {:ok, ips}
    else
      _ -> {:error, :dns_rejected}
    end
  end

  defp chain(_, _, _, _, depth) when depth > 8, do: {:error, :dns_rejected}

  defp chain(name, type, answers, seen, depth) do
    if MapSet.member?(seen, name) do
      {:error, :dns_rejected}
    else
      matching = Enum.filter(answers, &(dns_name(:inet_dns.rr(&1, :domain)) == name))
      cnames = Enum.filter(matching, &(:inet_dns.rr(&1, :type) == :cname))
      addresses = Enum.filter(matching, &(:inet_dns.rr(&1, :type) in [:a, :aaaa]))

      cond do
        length(cnames) == 1 and addresses == [] ->
          chain(
            dns_name(:inet_dns.rr(hd(cnames), :data)),
            type,
            answers,
            MapSet.put(seen, name),
            depth + 1
          )

        cnames != [] ->
          {:error, :dns_rejected}

        true ->
          all = Enum.filter(answers, &(:inet_dns.rr(&1, :type) in [:a, :aaaa]))

          if length(all) <= 16 and
               Enum.all?(
                 all,
                 &GlobalAddress.global?(GlobalAddress.normalize(:inet_dns.rr(&1, :data)))
               ) do
            {:ok,
             addresses
             |> Enum.filter(&(:inet_dns.rr(&1, :type) == type))
             |> Enum.map(&GlobalAddress.normalize(:inet_dns.rr(&1, :data)))}
          else
            {:error, :dns_rejected}
          end
      end
    end
  end

  defp dns_name(n), do: n |> List.to_string() |> String.downcase() |> String.trim_trailing(".")
end
