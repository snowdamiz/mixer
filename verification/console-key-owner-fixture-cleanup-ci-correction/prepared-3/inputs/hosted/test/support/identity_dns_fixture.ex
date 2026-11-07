defmodule MixerHosted.Identity.DNSFixture do
  @moduledoc false
  use GenServer
  def start_link(_opts \\ []), do: GenServer.start_link(__MODULE__, [])
  def configure(pid, mode), do: GenServer.call(pid, {:configure, mode})
  def info(pid), do: GenServer.call(pid, :info)

  def init(_) do
    {:ok, s} = :gen_udp.open(0, [:binary, ip: {127, 0, 0, 1}, active: true])
    {:ok, {_, port}} = :inet.sockname(s)
    {:ok, %{socket: s, port: port, mode: {:addresses, [{8, 8, 8, 8}]}, queries: []}}
  end

  def handle_call({:configure, mode}, _, s), do: {:reply, :ok, %{s | mode: mode}}
  def handle_call(:info, _, s), do: {:reply, Map.take(s, [:port, :queries]), s}

  def handle_info({:udp, socket, ip, port, raw}, s) do
    {:ok, msg} = :inet_dns.decode(raw)
    [query] = :inet_dns.msg(msg, :qdlist)
    name = :inet_dns.dns_query(query, :domain)
    type = :inet_dns.dns_query(query, :type)
    header = :inet_dns.msg(msg, :header)
    {answers, tc, delay} = answer(s.mode, name, type)
    header = :inet_dns.make_header(header, qr: true, aa: false, ra: true, tc: tc)
    reply = :inet_dns.make_msg(msg, header: header, anlist: answers) |> :inet_dns.encode()

    if delay > 0,
      do: Process.send_after(self(), {:reply, socket, ip, port, reply}, delay),
      else: :gen_udp.send(socket, ip, port, reply)

    mode =
      if match?({:rebind, _}, s.mode) and length(s.queries) == 1,
        do: {:addresses, [{127, 0, 0, 1}]},
        else: s.mode

    {:noreply, %{s | queries: [{name, type} | s.queries], mode: mode}}
  end

  def handle_info({:reply, s, ip, p, r}, state) do
    :gen_udp.send(s, ip, p, r)
    {:noreply, state}
  end

  defp answer({:rebind, ips}, name, type), do: answer({:addresses, ips}, name, type)
  defp answer({:delay, delay}, _, _), do: {[], false, delay}
  defp answer(:truncated, _, _), do: {[], true, 0}

  defp answer({:addresses, ips}, name, type) do
    rr =
      for ip <- ips,
          (tuple_size(ip) == 4 and type == :a) or (tuple_size(ip) == 8 and type == :aaaa),
          do: :inet_dns.make_rr(domain: name, type: type, class: :in, ttl: 120, data: ip)

    {rr, false, 0}
  end

  defp answer({:chain, count, loop}, name, type) do
    names = [name | Enum.map(1..count, &String.to_charlist("c#{&1}.fixture.invalid"))]
    pairs = Enum.zip(names, tl(names) ++ [if(loop, do: name, else: ~c"terminal.fixture.invalid")])

    cnames =
      Enum.map(pairs, fn {a, b} ->
        :inet_dns.make_rr(domain: a, type: :cname, class: :in, ttl: 120, data: b)
      end)

    terminal =
      if type == :a,
        do: [
          :inet_dns.make_rr(
            domain: ~c"terminal.fixture.invalid",
            type: :a,
            class: :in,
            ttl: 120,
            data: {8, 8, 8, 8}
          )
        ],
        else: []

    {cnames ++ terminal, false, 0}
  end

  def terminate(_, s), do: :gen_udp.close(s.socket)
end
