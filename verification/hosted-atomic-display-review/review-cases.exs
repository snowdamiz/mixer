  # New independent reviewer cases. Original 88 bodies remain byte-identical.
  defp review_corpus, do: Jason.decode!(File.read!("review-corpus.json"))

  test "R01 source-byte mixes match actual PostgreSQL and independent Python expected bytes" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    captured = for c <- review_corpus()["strings"] do
      text = c["value"]
      expected = Base.decode16!(c["expected_hex"], case: :lower)
      pg = scalar("SELECT convert_to($1::jsonb::text,'UTF8')", [text])
      assert pg == expected, c["label"]
      assert Codec.postgres_display(text) == expected, c["label"]
      display = independent_put(Map.put(base,"reason",text), ["actor",3], text)
      assert {:ok, encoded} = independent_sql_decode(display)
      assert encoded == Codec.encode(Codec.from_display(display))
      assert scalar("SELECT convert_to($1::jsonb::text,'UTF8')", [display]) == Codec.postgres_display(display)
      %{label: c["label"], text_hex: Codec.hex(text), pg_hex: Codec.hex(pg)}
    end
    assert Codec.postgres_display("é") != Codec.postgres_display("e\u0301")
    observe("review_string_parity", captured)
  end

  test "R02 UTF8 byte-length key order nested values and raw escape spellings match actual PostgreSQL" do
    objects = for c <- review_corpus()["objects"] do
      expected = Base.decode16!(c["expected_hex"], case: :lower)
      pg = scalar("SELECT convert_to($1::jsonb::text,'UTF8')", [c["value"]])
      assert pg == expected, c["label"]
      assert Codec.postgres_display(c["value"]) == expected
      %{label: c["label"], pg_hex: Codec.hex(pg)}
    end
    raw = for c <- review_corpus()["raw_inputs"] do
      pg = scalar("SELECT convert_to($1::text::jsonb::text,'UTF8')", [c["raw"]])
      assert pg == Base.decode16!(c["expected_hex"], case: :lower)
      assert Codec.postgres_display(Jason.decode!(c["raw"])) == pg
      %{label: c["label"], raw_hex: Codec.hex(c["raw"]), pg_hex: Codec.hex(pg)}
    end
    observe("review_object_raw_parity", %{objects: objects, raw: raw, closed_schema_not_expanded: true})
  end

  test "R03 independent mixed-control Unicode reasons store all columns and replay unchanged" do
    captured = for {c, index} <- Enum.with_index(review_corpus()["stored"], 1) do
      key = "review-display-" <> to_string(index)
      canonical = <<index::24>>
      assert {:ok, [201,body,event,false]} = attempt(key: key, canonical: canonical, reason: c["text"])
      before = display_correction_row(index)
      assert Codec.validate_row!(before) == :ok
      assert scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e WHERE event_id=$1::text::numeric", [to_string(index)])
      assert {:ok, [201,^body,^event,true]} = attempt(key: key, canonical: canonical, reason: c["text"])
      assert display_correction_row(index) == before
      %{label: c["label"], text_hex: c["text_hex"], sql_row: true, elixir_row: "accepted", exact_replay: true, retained_row: display_correction_capture(before)}
    end
    n = length(captured)
    assert counts() == [n,n,n,to_string(n)]
    observe("review_stored_rows", captured)
  end

  test "R04 several decoded-equivalent retained serializations reject and exact originals replay" do
    assert {:ok, [201,body,event,false]} = attempt(reason: "\u000b\\u000B雪😀/")
    row = retained_row()
    variants = [
      {"hex-case", String.replace(row.display_bytes, "\"reason\": \"\\u000b", "\"reason\": \"\\u000B", global: false)},
      {"unicode-bmp", String.replace(row.display_bytes, "雪", "\\u96ea", global: false)},
      {"unicode-pair", String.replace(row.display_bytes, "😀", "\\ud83d\\ude00", global: false)},
      {"solidus", String.replace(row.display_bytes, "😀/", "😀\\/", global: false)},
      {"leading-space", " " <> row.display_bytes},
      {"compact", Jason.encode!(row.display_json)}
    ]
    captured = for {label,bytes} <- variants do
      refute bytes == row.display_bytes
      assert Jason.decode!(bytes) == row.display_json
      assert_raise ArgumentError, fn -> Codec.validate_row!(Map.put(row,:display_bytes,bytes)) end
      sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=$1", [bytes])
      assert_raise Postgrex.Error, fn -> scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e") end
      assert {:rejected,_,_} = attempt()
      assert counts() == [1,1,1,"1"]
      sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=$1", [row.display_bytes])
      assert {:ok, [201,^body,^event,true]} = attempt()
      assert retained_row() == row
      %{label: label, alternative_hex: Codec.hex(bytes), both_validators_rejected: true, exact_original_replay: true}
    end
    observe("review_equivalent_byte_rejection", %{original: display_correction_capture(row), variants: captured})
  end

  test "R05 mixed escaping and Unicode retain exact profile128 reason512 source byte limits" do
    base = Jason.decode!(File.read!("golden-vectors.json"))["expected_display"]
    captured = for {c,index} <- Enum.with_index(review_corpus()["bounds"], 1) do
      assert byte_size(c["profile"]) == 128
      assert byte_size(c["reason"]) == 512
      display = independent_put(Map.put(base,"reason",c["reason"]), ["actor",3], c["profile"])
      assert {:ok,encoded} = independent_sql_decode(display)
      assert encoded == Codec.encode(Codec.from_display(display))
      pg = scalar("SELECT convert_to($1::jsonb::text,'UTF8')", [display])
      assert pg == Codec.postgres_display(display)
      for invalid <- [independent_put(display,["actor",3],c["profile"] <> "a"), Map.put(display,"reason",c["reason"] <> "a")] do
        assert_raise ArgumentError, fn -> Codec.from_display(invalid) end
        assert {:rejected,_,_} = independent_sql_decode(invalid)
      end
      assert {:ok,[201,body,event,false]} = attempt(key: "review-bound-" <> to_string(index), canonical: <<index::32>>, reason: c["reason"])
      row = display_correction_row(index)
      assert Codec.validate_row!(row) == :ok
      assert {:ok,[201,^body,^event,true]} = attempt(key: "review-bound-" <> to_string(index), canonical: <<index::32>>, reason: c["reason"])
      assert display_correction_row(index) == row
      %{label: c["label"], text_hex: Codec.hex(c["reason"]), sql_row: true, elixir_row: "accepted", exact_replay: true, retained_row: display_correction_capture(row), profile_hex: Codec.hex(c["profile"]), pure_display_hex: Codec.hex(pg)}
    end
    before = counts()
    assert {:rejected,_,_} = attempt(key: "review-513", reason: hd(review_corpus()["bounds"])["reason"] <> "a")
    assert counts() == before
    observe("review_boundary_rows", captured)
  end

  test "R06 NUL and malformed UTF8 keys and nested strings cannot become valid stored rows" do
    invalid = [<<0>>, "a" <> <<0>> <> "b", <<0x80>>, <<0xBF>>, <<0xC0,0xAF>>, <<0xE0,0x80,0xAF>>, <<0xED,0xBF,0xBF>>, <<0xF0,0x80,0x80,0xAF>>, <<0xF4,0x90,0x80,0x80>>, <<0xF5,0x80,0x80,0x80>>, <<0xFE>>, <<0xFF>>, <<0xC2>>, <<0xE2,0x82>>, <<0xF0,0x9F,0x98>>]
    captured = for text <- invalid do
      for value <- [text, %{text => "value"}, ["valid",text]] do
        assert_raise ArgumentError, fn -> Codec.postgres_display(value) end
      end
      assert_raise Postgrex.Error, fn -> scalar("SELECT convert_from($1,'UTF8')", [text]) end
      assert {:rejected,_,_} = attempt(reason: text)
      assert counts() == [0,0,0,"0"]
      %{invalid_hex: Codec.hex(text), rejected: true}
    end
    observe("review_invalid_utf8_nul", captured)
  end
