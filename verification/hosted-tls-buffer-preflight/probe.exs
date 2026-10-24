defmodule Preflight.BoundedTCP do
  import Kernel, except: [send: 2]
  # Isolated prototype only. No TLS options, certificates, destinations, or tags change.
  def connect(address, port, opts, timeout) do
    case :gen_tcp.connect(address, port, cap(opts), timeout) do
      {:ok, socket} ->
        with :ok <- fixed_buffer(socket),
             :ok <- register_raw(socket) do
          {:ok,socket}
        else
          error -> :gen_tcp.close(socket); error
        end
      error -> error
    end
  end
  defp register_raw(socket) do
    if watcher = :persistent_term.get({__MODULE__, :watcher}, nil) do
      ref=make_ref()
      Kernel.send(watcher, {:raw_socket, self(), socket,ref})
      receive do
        {^ref,:ok}->:ok
      after
        500->{:error,:registration_timeout}
      end
    else
      {:error,:missing_watcher}
    end
  end
  def setopts(socket, opts) do
    # Avoid granting a read while recbuf has inflated the driver buffer.
    {activation, other}=Enum.split_with(opts,fn {key,_}->key==:active; _->false end)
    with :ok <- :inet.setopts(socket, other),
         :ok <- fixed_buffer(socket) do
      :inet.setopts(socket,cap(activation))
    end
  end
  defp fixed_buffer(socket) do
    if :persistent_term.get({__MODULE__, :fixed_buffer}, false) do
      with :ok <- :inet.setopts(socket, buffer: 16_384),
           {:ok,[buffer: 16_384]} <- :inet.getopts(socket,[:buffer]),do: :ok
    else
      :ok
    end
  end
  def getopts(socket, opts), do: :inet.getopts(socket, opts)
  def getstat(socket, opts), do: :inet.getstat(socket, opts)
  def peername(socket), do: :inet.peername(socket)
  def sockname(socket), do: :inet.sockname(socket)
  def port(socket), do: :inet.port(socket)
  def controlling_process(socket, pid), do: :gen_tcp.controlling_process(socket, pid)
  def send(socket, data), do: :gen_tcp.send(socket, data)
  def recv(socket, n, timeout), do: :gen_tcp.recv(socket, n, timeout)
  def shutdown(socket, how), do: :gen_tcp.shutdown(socket, how)
  def close(socket), do: :gen_tcp.close(socket)
  defp cap(opts), do: Enum.map(opts, fn
    {:active, n} when is_integer(n) and n > 0 -> {:active, 1}
    option -> option
  end)
end

defmodule Preflight.ClientPause do
  def after_request do
    Process.sleep(:persistent_term.get({__MODULE__, :ms}, 0))
  end
end

defmodule Preflight.Probe do
  use GenServer
  def start_link, do: GenServer.start_link(__MODULE__, nil)
  def init(_) do
    Process.send_after(self(), :sample, 1)
    {:ok, %{sockets: %{}, workers: MapSet.new(), pids: MapSet.new(), ports: MapSet.new(), seen: 0,
      max_active: 0, max_ssl_process_memory: 0, max_ssl_binary_references: 0,
      max_total_ssl_binary_references: 0, max_unique_ssl_binary_bytes: 0,
      max_ssl_mailbox: 0, max_worker_memory: 0, max_worker_binary_references: 0,
      max_raw_buffer: 0, max_raw_recbuf: 0, samples: 0}}
  end
  def handle_info({:raw_socket, worker, port,ref}, s) do
    send(worker,{ref,:ok})
    {:noreply, %{s | workers: MapSet.put(s.workers, worker), ports: MapSet.put(s.ports,port)}}
  end
  def handle_info({:register_socket, worker, socket, ref}, s) do
    # OTP29 opaque record inspection is test instrumentation only.
    pids=[elem(socket,2),elem(socket,3)]
    s=%{s | sockets: Map.put(s.sockets,worker,socket), workers: MapSet.put(s.workers,worker),
      ports: MapSet.put(s.ports,elem(socket,1)), pids: Enum.reduce(pids,s.pids,&MapSet.put(&2,&1)),
      seen: s.seen+1, max_active: max(s.max_active,map_size(s.sockets)+1)}
    send(worker,{ref,:ok})
    {:noreply,sample(s)}
  end
  def handle_info(:sample,s) do
    Process.send_after(self(),:sample,1)
    {:noreply,sample(s)}
  end
  def handle_call(:raw_ports,_,s), do: {:reply,MapSet.to_list(s.ports),s}
  def handle_call(:info,_,s) do
    s=sample(s)
    alive_pids=Enum.count(s.pids,&Process.alive?/1)
    alive_ports=Enum.count(s.ports,fn p -> :erlang.port_info(p) != :undefined end)
    result=Map.drop(s,[:sockets,:workers,:pids,:ports]) |> Map.merge(%{alive_ssl_processes: alive_pids,alive_raw_ports: alive_ports})
    {:reply,result,s}
  end
  defp sample(s) do
    owners=Enum.flat_map(s.ports,fn p ->
      case :erlang.port_info(p,:connected) do
        {:connected,pid}->if MapSet.member?(s.workers,pid),do: [],else: [pid]
        _->[]
      end
    end)
    # Pinned OTP29 supervision instrumentation captures sender before handshake too.
    related=Enum.flat_map(owners,fn pid ->
      try do
        case Process.info(pid,:dictionary) do
          {:dictionary,dict}->
            case Keyword.get(dict,:"$ancestors",[]) do
              [sup|_] when is_pid(sup)->
                :supervisor.which_children(sup) |> Enum.flat_map(fn
                  {_,child,_,_} when is_pid(child)->[child]
                  _->[]
                end)
              _->[]
            end
          _->[]
        end
      catch _,_->[] end
    end)
    s=%{s|pids: Enum.reduce(owners++related,s.pids,&MapSet.put(&2,&1))}
    live=Enum.filter(s.pids,&Process.alive?/1)
    infos=Enum.map(live,&Process.info(&1,[:memory,:binary,:message_queue_len])) |> Enum.reject(&is_nil/1)
    refs=Enum.flat_map(infos,& &1[:binary])
    per_process=Enum.map(infos,fn i -> Enum.reduce(i[:binary],0,fn {_,n,_},a -> a+n end) end)
    unique=Map.new(refs,fn {id,n,_}->{id,n} end) |> Map.values() |> Enum.sum()
    workers=Enum.map(s.workers,&Process.info(&1,[:memory,:binary])) |> Enum.reject(&is_nil/1)
    opts=Enum.map(s.ports,fn p -> case :inet.getopts(p,[:buffer,:recbuf]) do {:ok,o}->o; _->[] end end)
    sockets=Map.reject(s.sockets,fn {w,_}->not Process.alive?(w) end)
    %{s | sockets: sockets,samples: s.samples+1,
      max_ssl_process_memory: max(s.max_ssl_process_memory,Enum.max(Enum.map(infos,& &1[:memory]),fn->0 end)),
      max_ssl_binary_references: max(s.max_ssl_binary_references,Enum.max(per_process,fn->0 end)),
      max_total_ssl_binary_references: max(s.max_total_ssl_binary_references,Enum.sum(per_process)),
      max_unique_ssl_binary_bytes: max(s.max_unique_ssl_binary_bytes,unique),
      max_ssl_mailbox: max(s.max_ssl_mailbox,Enum.max(Enum.map(infos,& &1[:message_queue_len]),fn->0 end)),
      max_worker_memory: max(s.max_worker_memory,Enum.max(Enum.map(workers,& &1[:memory]),fn->0 end)),
      max_worker_binary_references: max(s.max_worker_binary_references,Enum.max(Enum.map(workers,fn i ->Enum.reduce(i[:binary],0,fn {_,n,_},a->a+n end) end),fn->0 end)),
      max_raw_buffer: max(s.max_raw_buffer,Enum.max(Enum.map(opts,&Keyword.get(&1,:buffer,0)),fn->0 end)),
      max_raw_recbuf: max(s.max_raw_recbuf,Enum.max(Enum.map(opts,&Keyword.get(&1,:recbuf,0)),fn->0 end))}
  end
end

defmodule Preflight.Run do
  @entry %{jwks_endpoint: %{host: "jwks.fixture.invalid",port: 443,path: "/keys"}}
  def run do
    {:ok,_}=Application.ensure_all_started(:ssl)
    {:ok,_}=Application.ensure_all_started(:mint)
    {:ok,_}=Application.ensure_all_started(:inets)
    {:ok,fixture}=MixerHosted.Identity.TLSFixture.start_link()
    authority=GenServer.call(fixture,:authority)
    versions=%{elixir: System.version(),otp: :erlang.system_info(:otp_release)|>List.to_string(),
      erts: :erlang.system_info(:version)|>List.to_string(), ssl: Application.spec(:ssl,:vsn)|>List.to_string(),
      system: System.build_info(), openssl: System.cmd("openssl",["version"])|>elem(0),
      ssl_internal_active_n_before: Application.get_env(:ssl,:internal_active_n)}
    output=System.fetch_env!("PREFLIGHT_OUTPUT")
    cases=for variant <- [:baseline,:active_only,:capped], pause <- [0,20], iteration <- 1..3 do
      raw="HTTP/1.1 500 Error\r\nContent-Type: application/json\r\n\r\n"<>String.duplicate("x",8_388_608)
      MixerHosted.Identity.TLSFixture.configure(fixture,{:raw,raw})
      run_case(authority,variant,"four-8MiB-500-fastflood",pause,iteration)
    end
    body="{}"<>String.duplicate(" ",262_142)
    MixerHosted.Identity.TLSFixture.configure(fixture,{:body,body})
    success=for variant <- [:baseline,:capped], do: run_case(authority,variant,"four-256KiB-content-length",0,1)
    headers=MixerHosted.Identity.TLSFixture.response("")|>String.split("\r\n\r\n")|>hd()|>String.replace("Content-Length: 0","Transfer-Encoding: chunked")
    MixerHosted.Identity.TLSFixture.configure(fixture,{:raw,headers<>"\r\n\r\n40000\r\n"<>body<>"\r\n0\r\n\r\n"})
    chunked=run_case(authority,:capped,"four-256KiB-chunked",0,1)
    MixerHosted.Identity.TLSFixture.configure(fixture,:stall)
    stall=run_case(authority,:capped,"four-TLS-established-stall",0,1)
    slow=for {mode,iteration} <- [{:timeout,1}|Enum.map(1..5,&{:watchdog_cancel,&1})],
      do: Map.put(slow_handshake(authority.ca,mode),:iteration,iteration)
    MixerHosted.Identity.TLSFixture.configure(fixture,{:body,"{}"})
    {:ok,certificate_probe}=Preflight.Probe.start_link()
    :persistent_term.put({Preflight.BoundedTCP,:watcher},certificate_probe)
    bad_host=Mint.HTTP.connect(:https,authority.ip,authority.port,hostname: "wrong.fixture.invalid",protocols: [:http1],mode: :passive,
      transport_opts: [cb_info: {Preflight.BoundedTCP,:tcp,:tcp_closed,:tcp_error,:tcp_passive},verify: :verify_peer,cacerts: [authority.ca],timeout: 2_000,versions: [:"tlsv1.2",:"tlsv1.3"],recbuf: 16_384,buffer: 16_384])
    Process.sleep(30)
    certificate_observation=GenServer.call(certificate_probe,:info)
    GenServer.stop(certificate_probe)
    {:ok,tls12fixture}=MixerHosted.Identity.TLSFixture.start_link(versions: [:"tlsv1.2"])
    tls12authority=GenServer.call(tls12fixture,:authority)
    tls12=run_case(tls12authority,:capped,"four-TLS1.2-verified-success",0,1)
    GenServer.stop(tls12fixture)
    all_cases=cases++success++[chunked,stall,tls12]
    validate!(all_cases,slow,bad_host)
    ordinary_protocols=MixerHosted.Identity.TLSFixture.info(fixture).requests |> Enum.map(&Keyword.fetch!(&1.tls,:protocol)) |> Enum.uniq() |> Enum.map(&Atom.to_string/1)
    GenServer.stop(fixture)
    :persistent_term.erase({Preflight.BoundedTCP,:watcher})
    :persistent_term.erase({Preflight.ClientPause,:ms})
    :persistent_term.erase({Preflight.BoundedTCP,:fixed_buffer})
    versions=Map.put(versions,:ssl_internal_active_n_after,Application.get_env(:ssl,:internal_active_n))
    File.write!(Path.join(output,"results.json"),Jason.encode!(%{versions: versions,cases: all_cases,slow_handshake: slow,ordinary_fixture_protocols: ordinary_protocols,wrong_hostname: inspect(bad_host),wrong_hostname_resources: certificate_observation, assertions: "passed"},pretty: true))
    IO.puts("PREFLIGHT_COMPLETE "<>Path.join(output,"results.json"))
  end
  defp run_case(a,variant,label,pause,iteration) do
    {:ok,probe}=Preflight.Probe.start_link()
    :persistent_term.put({Preflight.BoundedTCP,:watcher},probe)
    :persistent_term.put({Preflight.ClientPause,:ms},pause)
    :persistent_term.put({Preflight.BoundedTCP,:fixed_buffer},variant==:capped)
    start=System.monotonic_time(:millisecond)
    mod=if variant==:baseline, do: Preflight.Baseline, else: Preflight.Capped
    results=Task.async_stream(1..4,fn _ ->
      mod.fetch_fixture(@entry,a.ip,a.port,System.monotonic_time(:millisecond)+2_000,[a.ca],probe)
    end,max_concurrency: 4,timeout: 3_000)|>Enum.map(fn {:ok,r}->case r do {:ok,c}->%{result: "ok",bytes: byte_size(c.body),metrics: c.metrics}; {:error,r}->%{result: "error",reason: inspect(r)} end end)
    elapsed=System.monotonic_time(:millisecond)-start
    Process.sleep(30)
    observation=GenServer.call(probe,:info)
    GenServer.stop(probe)
    IO.puts("CASE #{variant} #{label} pause=#{pause} n=#{iteration} ms=#{elapsed} ssl_bins=#{observation.max_ssl_binary_references} alive_ports=#{observation.alive_raw_ports}")
    Map.merge(observation,%{variant: variant,case: label,pause_after_request_ms: pause,iteration: iteration,elapsed_ms: elapsed,results: results})
  end
  defp slow_handshake(ca,mode) do
    {:ok,listener}=:gen_tcp.listen(0,[:binary,active: false,ip: {127,0,0,1},reuseaddr: true])
    {:ok,{_,port}}=:inet.sockname(listener)
    parent=self()
    acceptor=spawn(fn -> accept_slow(listener,parent) end)
    {:ok,probe}=Preflight.Probe.start_link()
    :persistent_term.put({Preflight.BoundedTCP,:watcher},probe)
    :persistent_term.put({Preflight.BoundedTCP,:fixed_buffer},true)
    start=System.monotonic_time(:millisecond)
    workers=for _ <-1..4 do
      Task.async(fn -> Preflight.Capped.fetch_fixture(@entry,{127,0,0,1},port,System.monotonic_time(:millisecond)+2_000,[ca],probe) end)
    end
    if mode==:watchdog_cancel do
      wait_ports(probe,4,200)
      Process.sleep(10)
      Enum.each(workers,&Process.unlink(&1.pid))
      Enum.each(workers,&Process.exit(&1.pid,:kill))
      # Stand-in for flight watchdog retaining raw TCP socket before SSL creation.
      Enum.each(GenServer.call(probe,:raw_ports),&:gen_tcp.close/1)
    end
    results=Enum.map(workers,fn t->
      if mode==:timeout,do: Task.await(t,3_000)|>inspect(),else:
        (receive do {:DOWN,ref,:process,_,reason} when ref==t.ref -> inspect(reason) after 1_000->"missing_down" end)
    end)
    elapsed=System.monotonic_time(:millisecond)-start
    Process.sleep(30)
    observation=GenServer.call(probe,:info)
    server_ports=for _ <-1..4 do receive do {:slow_server_port,p}->p after 100->nil end end
    server_closed=Enum.count(server_ports,&drained_closed/1)
    Enum.each(server_ports,fn p->if p,do: :gen_tcp.close(p) end)
    :gen_tcp.close(listener)
    Process.exit(acceptor,:kill)
    GenServer.stop(probe)
    Map.merge(observation,%{case: "four-server-withholds-TLS-handshake",mode: mode,elapsed_ms: elapsed,results: results,server_sockets_closed: server_closed})
  end
  defp validate!(cases,slow,bad_host) do
    unless match?({:error,_},bad_host),do: raise("hostname verification did not reject")
    for c <- cases do
      unless c.alive_raw_ports==0 and c.alive_ssl_processes==0,do: raise("client resources retained")
      unless length(c.results)==4,do: raise("four flight result missing")
      if c.variant==:capped do
        unless c.max_raw_buffer==16_384,do: raise("driver buffer cap failed")
        if c.case=="four-8MiB-500-fastflood" do
          unless c.max_ssl_binary_references<524_288 and c.max_total_ssl_binary_references<2_097_152,
            do: raise("hostile buffer regression threshold exceeded")
        end
      end
      if String.contains?(c.case,"fastflood") or String.contains?(c.case,"stall") do
        unless Enum.all?(c.results,&(&1.result=="error")),do: raise("hostile response accepted")
      else
        unless Enum.all?(c.results,&(&1.result=="ok")),do: raise("valid response rejected")
      end
      unless c.elapsed_ms<2_300,do: raise("flight deadline overrun")
    end
    for c <- slow do
      unless c.alive_raw_ports==0 and c.alive_ssl_processes==0 and c.server_sockets_closed==4,
        do: raise("pre-handshake lifecycle cleanup failed")
      unless c.elapsed_ms<2_300,do: raise("pre-handshake deadline overrun")
    end
  end
  defp wait_ports(probe,n,remaining) do
    if length(GenServer.call(probe,:raw_ports))<n and remaining>0 do
      Process.sleep(1)
      wait_ports(probe,n,remaining-1)
    end
  end
  defp drained_closed(p) do
    case :gen_tcp.recv(p,0,50) do
      {:ok,_}->drained_closed(p)
      {:error,:closed}->true
      _->false
    end
  end
  defp accept_slow(listener,parent) do
    case :gen_tcp.accept(listener,3_000) do
      {:ok,p}->
        :gen_tcp.controlling_process(p,parent)
        send(parent,{:slow_server_port,p})
        accept_slow(listener,parent)
      _->:ok
    end
  end
end
Preflight.Run.run()
