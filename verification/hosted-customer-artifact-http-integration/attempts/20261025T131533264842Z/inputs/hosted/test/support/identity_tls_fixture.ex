defmodule MixerHosted.Identity.TLSFixture do
  @moduledoc false
  use GenServer
  def start_link(opts \\ []), do: GenServer.start_link(__MODULE__, opts)
  def configure(pid, response), do: GenServer.call(pid, {:configure, response})
  def info(pid), do: GenServer.call(pid, :info)

  def init(opts) do
    Process.flag(:trap_exit, true)
    {:ok, _} = Application.ensure_all_started(:ssl)

    dir =
      Path.join(
        System.tmp_dir!(),
        "mixer-key-owner-tls-#{Base.url_encode64(:crypto.strong_rand_bytes(16), padding: false)}"
      )

    File.mkdir!(dir)
    File.chmod!(dir, 0o700)

    {cert, key, ca} =
      try do
        run([
          "req",
          "-x509",
          "-newkey",
          "rsa:2048",
          "-nodes",
          "-keyout",
          dir <> "/ca.key",
          "-out",
          dir <> "/ca.pem",
          "-days",
          "1",
          "-subj",
          "/CN=Mixer Fixture CA"
        ])

        run([
          "req",
          "-new",
          "-newkey",
          "rsa:2048",
          "-nodes",
          "-keyout",
          dir <> "/leaf.key",
          "-out",
          dir <> "/leaf.csr",
          "-subj",
          "/CN=jwks.fixture.invalid"
        ])

        File.write!(
          dir <> "/leaf.ext",
          "subjectAltName=DNS:jwks.fixture.invalid\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n"
        )

        if Keyword.get(opts, :validity) in [:future, :expired] do
          File.write!(dir <> "/index.txt", "")
          File.write!(dir <> "/serial", "01\n")

          File.write!(
            dir <> "/ca.conf",
            "[ca]\ndefault_ca=fixture\n[fixture]\ndatabase=#{dir}/index.txt\nserial=#{dir}/serial\nnew_certs_dir=#{dir}\ncertificate=#{dir}/ca.pem\nprivate_key=#{dir}/ca.key\ndefault_md=sha256\npolicy=policy\n[policy]\ncommonName=supplied\n"
          )

          delta = if Keyword.get(opts, :validity) == :future, do: 86_400, else: -172_800
          starts = Calendar.strftime(DateTime.add(DateTime.utc_now(), delta), "%y%m%d%H%M%SZ")

          ends =
            Calendar.strftime(DateTime.add(DateTime.utc_now(), delta + 86_400), "%y%m%d%H%M%SZ")

          run([
            "ca",
            "-batch",
            "-notext",
            "-config",
            dir <> "/ca.conf",
            "-in",
            dir <> "/leaf.csr",
            "-out",
            dir <> "/leaf.pem",
            "-startdate",
            starts,
            "-enddate",
            ends,
            "-extfile",
            dir <> "/leaf.ext"
          ])
        else
          run([
            "x509",
            "-req",
            "-in",
            dir <> "/leaf.csr",
            "-CA",
            dir <> "/ca.pem",
            "-CAkey",
            dir <> "/ca.key",
            "-CAcreateserial",
            "-out",
            dir <> "/leaf.pem",
            "-days",
            "1",
            "-extfile",
            dir <> "/leaf.ext"
          ])
        end

        [{_, cert, _}] = :public_key.pem_decode(File.read!(dir <> "/leaf.pem"))

        cert =
          if Keyword.get(opts, :tampered_signature, false) do
            n = byte_size(cert) - 1
            <<prefix::binary-size(^n), last>> = cert
            prefix <> <<:erlang.bxor(last, 1)>>
          else
            cert
          end

        [{kind, key, _}] = :public_key.pem_decode(File.read!(dir <> "/leaf.key"))
        [{_, ca, _}] = :public_key.pem_decode(File.read!(dir <> "/ca.pem"))
        {cert, {kind, key}, ca}
      after
        File.rm_rf!(dir)
      end

    ip = Keyword.get(opts, :ip, {127, 0, 0, 1})
    family = if tuple_size(ip) == 8, do: :inet6, else: :inet

    {:ok, listener} =
      :ssl.listen(Keyword.get(opts, :port, 0), [
        family,
        :binary,
        ip: ip,
        active: false,
        reuseaddr: true,
        cert: cert,
        key: key,
        versions: Keyword.get(opts, :versions, [:"tlsv1.2", :"tlsv1.3"])
      ])

    {:ok, {_, port}} = :ssl.sockname(listener)
    owner = self()
    acceptor = spawn_link(fn -> accept(listener, owner) end)

    {:ok,
     %{
       listener: listener,
       acceptor: acceptor,
       port: port,
       ip: ip,
       ca: ca,
       sockets: %{},
       requests: [],
       accepted: 0,
       closed: 0,
       max_active: 0,
       response: {:body, "{}"},
       key_dir_removed: not File.exists?(dir)
     }}
  end

  defp run(args) do
    case System.cmd("openssl", args, stderr_to_stdout: true) do
      {_, 0} -> :ok
      {out, n} -> raise "openssl fixture failed #{n}: #{String.slice(out, 0, 200)}"
    end
  end

  defp accept(listener, owner) do
    case :ssl.transport_accept(listener, 100) do
      {:ok, socket} ->
        pid =
          spawn_link(fn ->
            receive do
              :go -> serve(socket, owner)
            end
          end)

        :ok = :ssl.controlling_process(socket, pid)
        send(owner, {:accepted, pid, socket})
        send(pid, :go)
        accept(listener, owner)

      {:error, :timeout} ->
        accept(listener, owner)

      _ ->
        :ok
    end
  end

  defp serve(socket, owner) do
    try do
      with {:ok, socket} <- :ssl.handshake(socket, 3_000),
           {:ok, request} <- request(socket, "") do
        {:ok, info} = :ssl.connection_information(socket, [:sni_hostname, :protocol])
        response = GenServer.call(owner, {:request, request, info})
        respond(socket, response)
        # Observe client close even for keepalive/stall responses.
        :ssl.recv(socket, 0, 3_000)
      end
    after
      :ssl.close(socket)
      send(owner, {:closed, self()})
    end
  end

  defp request(socket, acc) do
    if String.contains?(acc, "\r\n\r\n") do
      {:ok, acc}
    else
      case :ssl.recv(socket, 0, 2_000) do
        {:ok, data} when byte_size(acc) + byte_size(data) < 4096 -> request(socket, acc <> data)
        error -> error
      end
    end
  end

  defp respond(socket, {:body, body}), do: :ssl.send(socket, response(body))
  defp respond(socket, {:raw, raw}), do: :ssl.send(socket, raw)

  defp respond(socket, {:drip, parts, delay}) do
    Enum.each(parts, fn part ->
      :ssl.send(socket, part)
      Process.sleep(delay)
    end)
  end

  defp respond(socket, {:barrier, recipient, raw}) do
    send(recipient, {:tls_response_ready, self()})

    receive do
      :release_response -> :ssl.send(socket, raw)
    after
      2_500 -> :ok
    end
  end

  defp respond(_, :stall), do: Process.sleep(3_000)

  def response(body, extra \\ []) do
    date = :httpd_util.rfc1123_date() |> List.to_string()

    headers =
      [
        {"Date", date},
        {"Cache-Control", "max-age=120"},
        {"Content-Type", "application/jwk-set+json"},
        {"Content-Length", Integer.to_string(byte_size(body))}
      ] ++ extra

    "HTTP/1.1 200 OK\r\n" <>
      Enum.map_join(headers, "", fn {k, v} -> k <> ": " <> v <> "\r\n" end) <> "\r\n" <> body
  end

  def handle_call({:configure, r}, _, s), do: {:reply, :ok, %{s | response: r}}
  def handle_call(:info, _, s), do: {:reply, Map.drop(s, [:response, :listener, :ca]), s}
  def handle_call(:authority, _, s), do: {:reply, Map.take(s, [:ip, :port, :ca]), s}

  def handle_call({:request, request, tls}, _, s),
    do: {:reply, s.response, %{s | requests: [%{request: request, tls: tls} | s.requests]}}

  def handle_info({:accepted, pid, socket}, s),
    do:
      {:noreply,
       %{
         s
         | sockets: Map.put(s.sockets, pid, socket),
           accepted: s.accepted + 1,
           max_active: max(s.max_active, map_size(s.sockets) + 1)
       }}

  def handle_info({:closed, pid}, s),
    do: {:noreply, %{s | sockets: Map.delete(s.sockets, pid), closed: s.closed + 1}}

  def handle_info({:EXIT, _, _}, s), do: {:noreply, s}

  def terminate(_, s) do
    :ssl.close(s.listener)
    Process.exit(s.acceptor, :kill)

    Enum.each(s.sockets, fn {pid, socket} ->
      :ssl.close(socket)
      Process.exit(pid, :kill)
    end)
  end
end
