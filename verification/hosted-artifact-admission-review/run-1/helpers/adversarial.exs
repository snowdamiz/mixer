defmodule IndependentAdmissionReview do
  alias MixerHosted.Protocol.{ArtifactAdmission,ArtifactCBOR,ArtifactJSON,ArtifactV3Policy}
  @uint 18_446_744_073_709_551_615
  def hash(b),do: Base.encode16(:crypto.hash(:sha256,b),case: :lower)
  def envelope(s,p),do: "{\"payload\":"<>Jason.encode!(Base.encode64(p))<>",\"signed_manifest\":"<>s<>"}"
  def save(out,kind,bytes) do
    name="inputs/"<>hash(bytes)<>"."<>kind
    File.write!(Path.join(out,name),bytes)
    name
  end
  def roots_json(roots),do: Enum.map(roots,fn r -> Map.update!(r,"public_key",&Base.encode64/1) end)
  def result(fun) do
    try do
      case fun.() do
        {:ok,_}->%{accepted: true,kind: "ok"}
        {:ok,_,_}->%{accepted: true,kind: "ok"}
        {:ok,_,_,_}->%{accepted: true,kind: "ok"}
        {:error,r} when is_atom(r)->%{accepted: false,kind: "closed_error",reason: Atom.to_string(r)}
        true->%{accepted: true,kind: "boolean"}
        false->%{accepted: false,kind: "boolean"}
        other->%{accepted: false,kind: "unexpected_result",detail: inspect(other,limit: 4)}
      end
    rescue e -> %{accepted: false,kind: "exception",detail: Exception.message(e)}
    catch k,v -> %{accepted: false,kind: "throw_or_exit",detail: inspect({k,v},limit: 4)}
    end
  end
  def record(out,name,mode,input,payload,host,roots,now,want,go \\ true) do
    row=%{name: name,mode: mode,input: save(out,"input",input),inputSHA256: hash(input),inputBytes: byte_size(input),payload: save(out,"payload",payload),payloadSHA256: hash(payload),expected: want,go: go,hostETF: save(out,"etf",:erlang.term_to_binary(host)),rootsETF: save(out,"etf",:erlang.term_to_binary(roots)),nowETF: save(out,"etf",:erlang.term_to_binary(now))}
    row=if go,do: Map.merge(row,%{host: host,roots: roots_json(roots),now: now}),else: row
    actual=result(fn -> case mode do
      "signed"-> ArtifactAdmission.admit_signed(input,payload,host,roots,now)
      "envelope"-> ArtifactAdmission.admit(input,host,roots,now)
      "json"->ArtifactJSON.decode(input,6_291_456)
      "preflight"->ArtifactJSON.preflight(input,6_291_456)
    end end)
    row=Map.put(row,:result,actual)
    unless actual.accepted==want and actual.kind not in ["exception","throw_or_exit","unexpected_result"],do: raise("#{name}: #{inspect(actual)} expected #{want}")
    File.write!(Path.join(out,"cases.jsonl"),Jason.encode!(row)<>"\n",[:append])
    row
  end
  def sign(m,key,domain \\ "mixer.artifact.v3\0") do
    {:ok,c}=ArtifactCBOR.encode(m)
    signature=:crypto.sign(:eddsa,:none,domain<>c,[key,:ed25519])
    Jason.encode!(%{"manifest"=>m,"signature"=>Base.encode64(signature)})
  end
  def observe(out,name,bytes,fun) do
    parent=self(); ref=make_ref()
    {pid,mon}=spawn_monitor(fn ->
      :erlang.garbage_collect();before=Process.info(self(),[:memory,:reductions])|>Map.new();start=System.monotonic_time(:microsecond)
      res=result(fn -> fun.(bytes) end)
      elapsed=System.monotonic_time(:microsecond)-start
      afters=Process.info(self(),[:memory,:reductions,:binary])|>Map.new()
      send(parent,{ref,%{name: name,input: save(out,"observation",bytes),inputBytes: byte_size(bytes),inputSHA256: hash(bytes),result: res,elapsedMicroseconds: elapsed,reductions: afters.reductions-before.reductions,processMemoryBefore: before.memory,processMemoryAfter: afters.memory,referencedBinaryBytesAfter: Enum.sum(for {_,s,_}<-afters.binary,do: s)}})
    end)
    sampler=fn recur,high ->
      high=case Process.info(pid,:memory) do {:memory,n}->max(high,n);nil->high end
      receive do
        {^ref,row}->receive do {:DOWN,^mon,:process,^pid,:normal}->:ok end;Map.put(row,:sampledProcessMemoryHigh,high)
        {:DOWN,^mon,:process,^pid,why}->raise("observation child: #{inspect(why)}")
      after 1->recur.(recur,high)
      end
    end
    sampler.(sampler,0)
  end
  def main(fpath,out) do
    File.mkdir_p!(Path.join(out,"inputs"))
    f=Jason.decode!(File.read!(fpath));h=f["host"];p=Base.decode64!(f["payload"]);now=f["verification_time_unix"]
    roots=Enum.map(f["roots"],fn r->Map.update!(r,"public_key",&Base.decode64!/1) end)
    m=f["signed_manifest"]["manifest"];s=Jason.encode!(f["signed_manifest"])
    {pub,key}=:crypto.generate_key(:eddsa,:ed25519)
    eroots=[hd(roots)|>Map.put("public_key",pub)]
    call=fn n,b,w->record(out,n,"signed",b,p,h,roots,now,w) end
    call.("fixture-reencoded-json-same-signature",s,true)
    call.("valid-escaped-field-name",String.replace(s,"\"manifest\":","\"\\u006danifest\":"),true)
    for {name,raw} <- [{"negative-zero","-0"},{"fraction","1.0"},{"exponent","1e0"},{"uint-overflow","18446744073709551616"},{"uint-long-zero-prefix","0001"}] do
      b=String.replace(s,"\"created_at_unix\":"<>Integer.to_string(m["created_at_unix"]),"\"created_at_unix\":"<>raw)
      call.(name,b,false)
    end
    for {name,b} <- [
      {"escaped-equivalent-nested-key",String.replace(s,"\"organization\":","\"\\u006frganization\":\"other\",\"organization\":")},
      {"unicode-case-sensitive-key",String.replace(s,"\"key_id\":","\"Key_id\":")},
      {"invalid-utf8-in-id",String.replace(s,m["release_id"],<<255>>)},
      {"lone-high-surrogate",String.replace(s,m["release_id"],"\\uD800")},
      {"lone-low-surrogate",String.replace(s,m["release_id"],"\\uDC00")},
      {"reversed-surrogates",String.replace(s,m["release_id"],"\\uDC00\\uD800")},
      {"valid-surrogate-pair-non-ascii-id",String.replace(s,m["release_id"],"\\uD83D\\uDE00")},
      {"literal-null",String.replace(s,"\"asset_hashes\":{}","\"asset_hashes\":null")},
      {"trailing-json",s<>" false"},
      {"invalid-escape",String.replace(s,m["release_id"],"\\x41")},
      {"control-character",String.replace(s,m["release_id"],<<1>>)}
    ],do: call.(name,b,false)
    # Semantically invalid, but cryptographically signed: both implementations must reject.
    changes=[{"created-zero",["created_at_unix"],0},{"state-inverted",["state_min"],m["state_max"]+1},{"assets-present",["asset_hashes"],%{"x"=>String.duplicate("a",64)}},{"compression-gzip",["compression"],"gzip"},{"ui-unsupported",["ui_schema"],2},{"fuel-over",["limits","fuel"],1_000_001},{"memory-zero",["limits","memory_bytes"],0},{"startup-over",["limits","startup_milliseconds"],60_001},{"capability-unknown",["capability_hashes"],%{"unknown"=>String.duplicate("a",64)}},{"source-uppercase",["source_commit"],String.duplicate("A",40)}]
    for {name,path,v}<-changes do
      mm=put_in(m,path,v);false=ArtifactV3Policy.manifest?(mm)
      record(out,name,"signed",sign(mm,key),p,h,eroots,now,false)
    end
    descriptor=m["capability_grants"];entries=descriptor["entries"]
    for {name,es,want}<- [{"empty-grants",[],true},{"grant-duplicate",[hd(entries),hd(entries)],false},{"grant-reversed",Enum.reverse(entries),false},{"grant-unbound",[Map.put(hd(entries),"schema_sha256",String.duplicate("0",64))],false},{"grant-empty-arrays",Enum.map(entries,fn e->Enum.reduce(~w(permissions origins methods namespaces),e,&Map.put(&2,&1,[])) end),true}] do
      mm=put_in(m,["capability_grants","entries"],es)
      ^want=ArtifactV3Policy.manifest?(mm)
      record(out,name,"signed",sign(mm,key),p,h,eroots,now,want)
    end
    # Valid max uint64 values and exact JSON/CBOR integers beyond double precision.
    wide=m|>Map.put("created_at_unix",@uint)|>Map.put("state_min",9_007_199_254_740_993)|>Map.put("state_max",@uint)
    wh=Map.put(h,"state_version",9_007_199_254_740_993)
    record(out,"wide-integers","signed",sign(wide,key),p,wh,eroots,now,true)
    record(out,"wide-integer-state-below","signed",sign(wide,key),p,Map.put(wh,"state_version",9_007_199_254_740_992),eroots,now,false)
    for domain<-["mixer.artifact.v2\0","mixer.assignment.v3\0","mixer.artifact.v3", ""] do
      record(out,"domain-"<>hash(domain),"signed",sign(m,key,domain),p,h,eroots,now,false)
    end
    record(out,"payload-same-size-mutation","signed",sign(m,key),:binary.copy("!",byte_size(p)),h,eroots,now,false)
    signed=sign(m,key);r=hd(eroots)
    root_cases=[{"root-count-one",eroots,true},{"root-count128",eroots++Enum.map(1..127,fn i->Map.put(r,"key_id","unrelated#{i}") end),true},{"root-count129",eroots++Enum.map(1..128,fn i->Map.put(r,"key_id","unrelated#{i}") end),false},{"root-duplicate",[r,r],false},{"unrelated-malformed-public-key",[r,r|>Map.put("key_id","other")|>Map.put("public_key",<<0>>)],false},{"unrelated-no-role",[r,r|>Map.put("key_id","other")|>Map.put("artifact",false)|>Map.put("assignment",false)],false},{"unrelated-bad-scope",[r,r|>Map.put("key_id","other")|>Map.put("scope",Map.put(r["scope"],"platform","web"))],false},{"root-not-before-inclusive",[Map.put(r,"not_before_unix",now)],true},{"root-not-after-exclusive",[Map.put(r,"not_after_unix",now)],false},{"root-no-expiry",[Map.put(r,"not_after_unix",0)],true},{"root-time-invalid-interval",[r|>Map.put("not_before_unix",now)|>Map.put("not_after_unix",now)],false},{"root-assignment-only",[Map.put(r,"artifact",false)],false},{"root-revoked",[Map.put(r,"revoked",true)],false},{"wrong-root-key",[Map.put(r,"public_key",<<0::256>>)],false},{"wrong-scope",[Map.put(r,"scope",Map.put(r["scope"],"app","different"))],false}]
    for {name,rs,want}<-root_cases,do: record(out,name,"signed",signed,p,h,rs,now,want)
    for {name,value} <- [{"host-nil",nil},{"host-atom",:host},{"host-tuple",{}},{"host-improper",[h|:tail]},{"host-struct",%URI{}},{"host-missing",Map.delete(h,"limits")},{"host-extra",Map.put(h,"extra",1)},{"host-limits-nil",Map.put(h,"limits",nil)},{"host-caps-struct",Map.put(h,"capability_hashes",%URI{})},{"host-scope-list",Map.put(h,"scope",[])},{"host-protocol-float",Map.put(h,"protocol",3.0)},{"host-now-wide",Map.put(h,"state_version",@uint+1)}] do
      record(out,name,"signed",signed,p,value,eroots,now,false,false)
    end
    for {name,value} <- [{"roots-nil",nil},{"roots-atom",:roots},{"roots-map",r},{"roots-improper",[r|:tail]},{"roots-entry-nil",[r,nil]},{"roots-entry-struct",[%URI{}]},{"root-boolean-string",[Map.put(r,"artifact","true")]},{"root-boolean-nil",[Map.put(r,"revoked",nil)]},{"root-extra",[Map.put(r,"extra",1)]},{"root-time-float",[Map.put(r,"not_before_unix",0.0)]}] do
      record(out,name,"signed",signed,p,h,value,now,false,false)
    end
    for {name,v}<- [{"now-negative",-1},{"now-float",1.0},{"now-null",nil},{"now-overflow",@uint+1},{"now-struct",%URI{}}],do: record(out,name,"signed",signed,p,h,eroots,v,false,false)
    # Pre-Jason structural boundaries. Preflight does not establish JSON/Unicode/schema acceptance.
    exact=Jason.encode!(List.duplicate(List.duplicate(0,256),15)++[List.duplicate(0,239)])
    over=Jason.encode!(List.duplicate(List.duplicate(0,256),15)++[List.duplicate(0,240)])
    for {name,b,want}<- [{"items4096",exact,true},{"items4097",over,false},{"depth16",String.duplicate("[",16)<>"0"<>String.duplicate("]",16),true},{"depth17",String.duplicate("[",17)<>"0"<>String.duplicate("]",17),false},{"array256",Jason.encode!(List.duplicate(0,256)),true},{"array257",Jason.encode!(List.duplicate(0,257)),false},{"object256",Jason.encode!(Map.new(1..256,&{Integer.to_string(&1),0})),true},{"object257",Jason.encode!(Map.new(1..257,&{Integer.to_string(&1),0})),false},{"preflight-invalid-unicode-is-only-lexical",<<34,255,34>>,true}] do
      record(out,name,"preflight",b,p,h,eroots,now,want,false)
    end
    record(out,"decoder-rejects-invalid-unicode","json",<<34,255,34>>,p,h,eroots,now,false,false)
    full=envelope(signed,p)
    for {name,b}<- [{"envelope-escaped-duplicate",String.replace(full,"\"payload\":","\"\\u0070ayload\":\"eA==\",\"payload\":")},{"envelope-signed-duplicate",String.replace(full,"\"signed_manifest\":","\"signed_manifest\":{},\"signed_manifest\":")},{"envelope-extra-null",String.replace(full,"{","{\"extra\":null,",global: false)}] do
      record(out,name,"envelope",b,p,h,eroots,now,false,false)
    end
    for b64 <- ["eB==","eA=","eA","eA===","=AAA","AA=A","eA__","eA--","eA==\n","","A","/x==","//9="] do
      b="{\"signed_manifest\":"<>signed<>",\"payload\":"<>Jason.encode!(b64)<>"}"
      record(out,"bad-payload-base64-"<>hash(b64),"envelope",b,p,h,eroots,now,false,false)
    end
    # Tail-bit mutations of a correctly signed 64-byte signature.
    sm=Jason.decode!(signed);sig=sm["signature"];alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    {pos,_}=:binary.match(alphabet,binary_part(sig,85,1))
    badsig=binary_part(sig,0,85)<>binary_part(alphabet,pos+1,1)<>"=="
    record(out,"signature-noncanonical-tail","signed",Jason.encode!(Map.put(sm,"signature",badsig)),p,h,eroots,now,false)
    # Raw signed value includes internal whitespace; outer value-separator whitespace is envelope-only.
    stand=String.duplicate(" ",65_536-byte_size(signed))<>signed
    record(out,"standalone65536","signed",stand,p,h,eroots,now,true)
    record(out,"standalone65537","signed"," "<>stand,p,h,eroots,now,false)
    embedded="{"<>String.duplicate(" ",65_536-byte_size(signed))<>binary_part(signed,1,byte_size(signed)-1)
    record(out,"embedded65536","envelope",envelope(embedded,p),p,h,eroots,now,true,false)
    record(out,"embedded65537","envelope",envelope("{ "<>binary_part(embedded,1,byte_size(embedded)-1),p),p,h,eroots,now,false,false)
    record(out,"envelope-outside-span-whitespace","envelope","{\"signed_manifest\":"<>String.duplicate(" ",65_537)<>signed<>",\"payload\":"<>Jason.encode!(Base.encode64(p))<>"}",p,h,eroots,now,true,false)
    large=:binary.copy(<<197>>,4_194_304)
    lm=m|>Map.put("compressed_bytes",byte_size(large))|>Map.put("expanded_bytes",byte_size(large))|>Map.put("payload_sha256",hash(large))
    ls=sign(lm,key);body=envelope(ls,large);maxbody=body<>String.duplicate(" ",6_291_456-byte_size(body))
    record(out,"payload4194304","signed",ls,large,h,eroots,now,true)
    record(out,"payload4194305","signed",ls,large<>"x",h,eroots,now,false)
    record(out,"envelope6291456","envelope",maxbody,large,h,eroots,now,true,false)
    record(out,"envelope6291457","envelope",maxbody<>" ",large,h,eroots,now,false,false)
    oversized="{\"signed_manifest\":"<>ls<>",\"payload\":"<>Jason.encode!(Base.encode64(large<>"x"))<>"}"
    record(out,"encoded-length-same-ceiling-decoded-one-over","envelope",oversized,large,h,eroots,now,false,false)
    # Reconstruct retained checked value; equality binds each field and current policy.
    {:ok,checked}=ArtifactAdmission.admit(full,h,eroots,now)
    rows=for {name,c,hh,rr,nn,want}<- [{"ordinary",checked,h,eroots,now,true},{"struct-rebuilt-identical",struct!(ArtifactAdmission.Checked,Map.from_struct(checked)),h,eroots,now,true},{"revoked-current",checked,h,[Map.put(r,"revoked",true)],now,false},{"expired-current",checked,h,[Map.put(r,"not_after_unix",now+1)],now+1,false},{"host-current-runtime",checked,Map.put(h,"runtime",String.duplicate("0",64)),eroots,now,false},{"forged-success-map",%{valid: true},h,eroots,now,false}]++Enum.map(Map.keys(Map.from_struct(checked)),fn k->{"changed-"<>Atom.to_string(k),Map.put(checked,k,nil),h,eroots,now,false} end) do
      actual=result(fn -> ArtifactAdmission.recheck(c,hh,rr,nn) end)
      true=actual.accepted==want
      %{name: name,expected: want,result: actual,checkedETF: save(out,"etf",:erlang.term_to_binary(c)),hostETF: save(out,"etf",:erlang.term_to_binary(hh)),rootsETF: save(out,"etf",:erlang.term_to_binary(rr)),now: nn}
    end
    File.write!(Path.join(out,"rechecks.json"),Jason.encode!(rows,pretty: true))
    observations=[observe(out,"full-max-valid-envelope",maxbody,fn b->ArtifactAdmission.admit(b,h,eroots,now) end),observe(out,"one-over-envelope",maxbody<>" ",fn b->ArtifactAdmission.admit(b,h,eroots,now) end),observe(out,"same-encoded-bound-decoded-one-over",oversized,fn b->ArtifactAdmission.admit(b,h,eroots,now) end),observe(out,"early-depth100000",String.duplicate("[",100_000)<>"0"<>String.duplicate("]",100_000),&ArtifactJSON.preflight(&1,6_291_456)),observe(out,"early-integer60000digits",String.duplicate("9",60_000),&ArtifactJSON.preflight(&1,6_291_456)),observe(out,"max-items4096",exact,&ArtifactJSON.preflight(&1,6_291_456)),observe(out,"linear-string1MiB",Jason.encode!(:binary.copy("A",1_048_576)),&ArtifactJSON.preflight(&1,6_291_456)),observe(out,"linear-string5MiB",Jason.encode!(:binary.copy("A",5_242_880)),&ArtifactJSON.preflight(&1,6_291_456))]
    File.write!(Path.join(out,"independent-observations.json"),Jason.encode!(%{observations: observations,scope: "Inputs allocated before spawning. Process memory samples exclude off-heap binaries, native allocator and unsampled transient peaks. No RSS/concurrency/deployment guarantee. Keys process-local ephemeral; only public keys/signatures persisted."},pretty: true))
    count=File.stream!(Path.join(out,"cases.jsonl"))|>Enum.count()
    IO.puts("independent cases=#{count}; retained rechecks=#{length(rows)}; observations=#{length(observations)}")
  end
end
[fpath,out]=System.argv()
IndependentAdmissionReview.main(fpath,out)
