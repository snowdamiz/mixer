import hashlib,json,subprocess,datetime
from pathlib import Path
O=Path(__file__).resolve().parent
code='IO.inspect(%{otp: :erlang.system_info(:otp_release), public_key_library: :code.lib_dir(:public_key), public_key_beam: :code.which(:public_key), roots_count: length(:public_key.cacerts_get()), shapes: Enum.frequencies_by(:public_key.cacerts_get(), fn x -> cond do is_binary(x) -> :der; is_tuple(x) and tuple_size(x) == 3 and elem(x,0) == :cert and is_binary(elem(x,1)) -> :cert_der_decoded; true -> :unexpected end end)}, label: "OTP_CA_source")'
argv=['elixir','-e',code];r=subprocess.run(argv,capture_output=True,text=True)
(O/'otp-ca-source.log').write_text(r.stdout+r.stderr)
lib=Path(subprocess.check_output(['elixir','-e','IO.puts(:code.lib_dir(:public_key))'],text=True).strip())
files=[lib/'src/public_key.erl',lib/'src/pubkey_os_cacerts.erl',lib/'ebin/public_key.beam']
selected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
lines=files[0].read_text().splitlines();snippets={str(n+1):line for n,line in enumerate(lines) if 'combined_cert()' in line or 'cacerts_get()' in line}
(O/'otp-ca-source.json').write_text(json.dumps({'argv':argv,'exitCode':r.returncode,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':selected,'specificationLines':snippets,'output':'otp-ca-source.log','outputSHA256':hashlib.sha256((O/'otp-ca-source.log').read_bytes()).hexdigest()},indent=2)+'\n')
