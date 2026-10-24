  # Focused correction assertions. The prior 83 assertions remain verbatim.
  defp display_correction_texts do
    controls = Enum.map(1..31, fn c -> {"ascii-" <> Integer.to_string(c), <<c>>} end)
    literals = Enum.map(["\\u000B", "\\u000b", "\\u000E", "\\u001F", "prefix\\u000B\\u000b\\u000E", "\\\\u000B", "\\n", "\\t", "\\u2028", "snow雪\\u000B"], &{"literal", &1})
    unicode = Enum.map(["\u0080", "\u0085", "\u00a0", "e\u0301", "é", "雪", "😀", "\u2028", "\u2029", "\u2060", "\ufeff", "\uffff"], &{"utf8", &1})
    mixed = "\"\\/" <> IO.iodata_to_binary(Enum.map(1..31, &<<&1>>)) <> "\\u000B\\u000b\\u001F" <> "e\u0301雪😀\u2028\u2029" <> <<127>>
    controls ++ [{"ascii-127", <<127>>}, {"quote-backslash-solidus", "\"\\/"}] ++ literals ++ unicode ++ [{"mixed-all", mixed}]
  end

  defp display_correction_row(id) do
    values = sql("SELECT organization,project,event_id::text,event_cbor,event_hash,previous_hash,previous_state,current_state,display_json,display_bytes FROM mixer_hosted_release.audit_events WHERE event_id=$1::text::numeric", [to_string(id)]).rows |> hd()
    Map.new(Enum.zip([:organization,:project,:event_id,:event_cbor,:event_hash,:previous_hash,:previous_state,:current_state,:display_json,:display_bytes], List.update_at(values,2,&String.to_integer/1)))
  end

  defp display_correction_capture(row) do
    Map.new(row, fn {key,value} ->
      if key in [:event_cbor,:event_hash,:previous_hash,:previous_state,:current_state,:display_bytes],
        do: {key,%{encoding: "hex", value: Codec.hex(value)}}, else: {key,value}
    end)
  end

  @tag :display_correction
  test "D01 complete representable ASCII controls and mixed literal Unicode match actual PostgreSQL bytes" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    cases = for {label,text} <- display_correction_texts() do
      assert byte_size(text) <= 128
      d = independent_put(Map.put(base,"reason",text),["actor",3],text)
      {:ok, pg_cbor} = independent_sql_decode(d)
      assert pg_cbor == Codec.encode(Codec.from_display(d)), label
      pg = scalar("SELECT convert_to($1::jsonb::text,'UTF8')",[d])
      assert pg == Codec.postgres_display(d), label
      assert Jason.decode!(pg)["reason"] == text
      assert Jason.decode!(pg)["actor"] |> Enum.at(3) == text
      %{label: label, text_hex: Codec.hex(text), postgres_display_hex: Codec.hex(pg), exact_parity: true}
    end
    # Exercise the same formatter for object keys and nested strings without
    # claiming arbitrary objects are accepted by the closed audit decoder.
    key = "key\u000b\\u000B雪"
    value = %{key => [nil, 1, "\"\\\b\f\n\r\t\u001f", "\\u000B"]}
    assert scalar("SELECT convert_to($1::jsonb::text,'UTF8')",[value]) == Codec.postgres_display(value)
    observe("display_correction_parity", %{cases: cases, representable_c0: 31, ascii_del: true, mixed: true, object_key_same_formatter: true})
  end

  @tag :display_correction
  test "D02 every control mixed literal and Unicode reason is uploaded stored validated and exactly replayed" do
    results = for {{label,text},index} <- Enum.with_index(display_correction_texts(),1) do
      key = "display-correction-" <> to_string(index)
      canonical = <<index::16>>
      assert {:ok,[201,body,event,false]} = attempt(key: key, reason: text, canonical: canonical)
      before = display_correction_row(index)
      assert Codec.validate_row!(before) == :ok, label
      assert scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e WHERE event_id=$1::text::numeric",[to_string(index)])
      assert before.display_json["reason"] == text
      assert {:ok,[201,^body,^event,true]} = attempt(key: key, reason: text, canonical: canonical)
      assert display_correction_row(index) == before
      %{label: label, text_hex: Codec.hex(text), sql_row: true, elixir_row: "accepted", exact_replay: true, retained_row: display_correction_capture(before)}
    end
    n = length(results)
    assert counts() == [n,n,n,to_string(n)]
    observe("display_correction_uploaded_rows", %{rows: results, count: n, exact_replay: true, all_retained_columns_unchanged: true})
  end

  @tag :display_correction
  test "D03 original profile and reason byte boundaries remain exact with control expansion and UTF8" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    cases = for {profile,reason} <- [{String.duplicate(<<31>>,128),String.duplicate(<<11>>,512)}, {String.duplicate("é",64),String.duplicate("😀",128)}, {String.duplicate("\\u000B",21) <> "xy",String.duplicate("\\u001F",85) <> "xy"}] do
      assert byte_size(profile) == 128
      assert byte_size(reason) == 512
      d = independent_put(Map.put(base,"reason",reason),["actor",3],profile)
      {:ok, bytes} = independent_sql_decode(d)
      assert bytes == Codec.encode(Codec.from_display(d))
      pg = scalar("SELECT convert_to($1::jsonb::text,'UTF8')",[d])
      assert pg == Codec.postgres_display(d)
      assert byte_size(pg) <= 32_768
      %{profile_hex: Codec.hex(profile), reason_hex: Codec.hex(reason), postgres_display_hex: Codec.hex(pg), original_byte_bounds: true}
    end
    for {profile,reason} <- [{String.duplicate("p",129),""},{"p",String.duplicate(<<31>>,513)},{"p",String.duplicate("é",256) <> "a"}] do
      d = independent_put(Map.put(base,"reason",reason),["actor",3],profile)
      assert_raise ArgumentError, fn -> Codec.from_display(d) end
      assert {:rejected,_,_} = independent_sql_decode(d)
    end
    for {reason,index} <- Enum.with_index([String.duplicate(<<31>>,512),String.duplicate("😀",128)],1) do
      assert {:ok,[201,body,event,false]} = attempt(key: "boundary"<>to_string(index),reason: reason,canonical: <<index>>)
      row = display_correction_row(index)
      assert Codec.validate_row!(row) == :ok
      assert {:ok,[201,^body,^event,true]} = attempt(key: "boundary"<>to_string(index),reason: reason,canonical: <<index>>)
      assert display_correction_row(index) == row
    end
    before = counts()
    assert {:rejected,_,_} = attempt(key: "over-limit",reason: String.duplicate(<<31>>,513))
    assert counts() == before
    observe("display_correction_byte_bounds", %{cases: cases, profile_129_rejected: true, reason_513_rejected: true, stored_boundary_rows: 2, limits_not_changed: true})
  end

  @tag :display_correction
  test "D04 NUL malformed Unicode and invalid UTF8 are explicit invalid PostgreSQL storage" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    nul = Map.put(base,"reason",<<0>>)
    assert_raise ArgumentError, fn -> Codec.from_display(nul) end
    assert_raise ArgumentError, fn -> Codec.postgres_display(<<0>>) end
    assert_raise Postgrex.Error, fn -> scalar("SELECT convert_to($1::jsonb::text,'UTF8')",[nul]) end
    assert {:rejected,_,_} = attempt(reason: <<0>>)
    assert counts() == [0,0,0,"0"]
    malformed = for raw <- [~S({"reason":"\ud800"}),~S({"reason":"\udc00"}),~S({"reason":"\ud800\u0041"}),~S({"reason":"\ud800\ud800"}),~S({"reason":"\u0000"})] do
      error = assert_raise Postgrex.Error, fn -> scalar("SELECT $1::text::jsonb",[raw]) end
      %{raw_json_hex: Codec.hex(raw), postgres_code: error.postgres.code, rejected: true}
    end
    for invalid <- [<<255>>,<<0xC0,0x80>>,<<0xED,0xA0,0x80>>,<<0xF4,0x90,0x80,0x80>>] do
      assert_raise ArgumentError, fn -> Codec.postgres_display(invalid) end
      assert_raise ArgumentError, fn -> Codec.from_display(Map.put(base,"reason",invalid)) end
      assert_raise Postgrex.Error, fn -> scalar("SELECT convert_from($1,'UTF8')",[invalid]) end
    end
    # A proper surrogate pair is valid JSON input and becomes literal UTF8.
    assert scalar("SELECT $1::text::jsonb->>'reason'",[~S({"reason":"\ud83d\ude00"})]) == "😀"
    observe("display_correction_invalid_storage", %{nul_rejected: true, malformed_unicode: malformed, invalid_utf8_cases: 4, valid_surrogate_pair_control: true, successful_invalid_rows: 0})
  end

  @tag :display_correction
  test "D05 equivalent decoded JSON spelling cannot replace exact retained bytes" do
    text = <<11>> <> "\\u000B\\u000b" <> "雪"
    assert {:ok,[201,body,event,false]} = attempt(reason: text)
    row = retained_row()
    assert Codec.validate_row!(row) == :ok
    # Mutate only the actual control escape, identified with surrounding key
    # syntax. Literal backslash-u text must not be normalized or recased.
    original = "\"reason\": \"\\u000b"
    changed = "\"reason\": \"\\u000B"
    alternative = String.replace(row.display_bytes,original,changed,global: false)
    refute alternative == row.display_bytes
    assert Jason.decode!(alternative) == row.display_json
    assert_raise ArgumentError, fn -> Codec.validate_row!(Map.put(row,:display_bytes,alternative)) end
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=$1",[alternative])
    assert_raise Postgrex.Error, fn -> scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e") end
    assert {:rejected,_,_} = attempt()
    assert counts() == [1,1,1,"1"]
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=$1",[row.display_bytes])
    assert {:ok,[201,^body,^event,true]} = attempt(reason: text)
    assert retained_row() == row
    observe("display_correction_exact_equality", %{decoded_equivalence_does_not_authorize_replacement: true, case_variant_rejected_by_both_rows: true, exact_original_replay_restored: true, literal_case_preserved: true})
  end
