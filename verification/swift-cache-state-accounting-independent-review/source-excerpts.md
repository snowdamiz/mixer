# Source-bound excerpts

Exact frozen source hashes appear in custody.json. These are text evidence only.

## verification/swift-cache-state-implementation/correction-1/source/library/cache_state.rs

```text
104: #[repr(C)]
105: struct Progress {
106:     calls: u64,
107:     latch: u64,
108:     q: [u64; 16],
109: }
110: impl Progress {
111:     // Low byte is the absorbing terminal tag. Bits8..14 retain the first-free
112:     // pin as slot+1;0means absent. Remaining bits are a malformed header.
113:     fn terminal(&self) -> u64 {
114:         self.latch & 255
115:     }
116:     fn first_pin(&self) -> u64 {
117:         let n = self.latch >> 8;
118:         if n == 0 {
119:             ABSENT
120:         } else {
121:             n - 1
122:         }
123:     }
124:     fn latch_terminal(&mut self, n: u64) {
125:         self.latch = (self.latch & !255) | n;
126:     }
127:     fn remember_pin(&mut self, n: u64) {
128:         self.latch = (self.latch & 255) | if n == ABSENT { 0 } else { (n + 1) << 8 };
129:     }
130: }
131: #[repr(C)]
132: struct Paid {
133:     setup: u64,
134:     finish: u64,
135:     records: u64,
136: }
137: #[repr(C)]
138: struct SemanticReply {
139:     status: u64,
140:     reason: u64,
141:     debit: u64,
142: }
143: // A loan exists only after actual wire/profile checks and audited envelope
144: // success. The immutable config borrow and exclusive arena slice cannot resize.
145: struct Loan<'a> {
146:     record: &'a FixtureDecodedRecordV1<'a>,
147:     config: &'a Fixture,
148: }
149: fn ld(b: &[u8], at: usize) -> u64 {
150:     u64::from_le_bytes(
151:         *b[at..at + 8]
152:             .first_chunk::<8>()
153:             .expect("proved eight-byte range"),
154:     )
155: }
156: fn st(b: &mut [u8], at: usize, n: u64) {
157:     b[at..at + 8].copy_from_slice(&n.to_le_bytes());
158: }
159: fn cq(c: &Candidate2048, i: usize) -> u64 {
160:     ld(c, SC + 8 * i)
161: }
162: fn sq(c: &mut Candidate2048, i: usize, n: u64) {
163:     st(c, SC + 8 * i, n);
164: }
165: fn rr(b: &[u8], row: usize, field: usize) -> u64 {
166:     ld(b, RESIDENT.base + 64 * row + 8 * field)
167: }
168: fn pr(b: &[u8], row: usize, field: usize) -> u64 {
169:     ld(b, PIN.base + 48 * row + 8 * field)
170: }
171: fn pl(b: &[u8], row: usize, field: usize) -> u64 {
172:     ld(b, PLAN.base + 40 * row + 8 * field)
173: }
```

```text
246: fn merge(c: &mut Candidate2048) {
247:     let mut src = 512;
248:     let mut dst = 1024;
249:     let mut width = 1;
250:     while width < 64 {
251:         let mut base = 0;
252:         while base < 64 {
253:             let mut left = base;
254:             let mid = base + width;
255:             let end = base + 2 * width;
256:             let mut right = mid;
257:             for out in base..end {
258:                 let take_left = if left == mid {
259:                     false
260:                 } else if right == end {
261:                     true
262:                 } else {
263:                     #[cfg(test)]
264:                     SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
265:                     let a = ld(c, src + left * 8);
266:                     let b = ld(c, src + right * 8);
267:                     b == ABSENT || (a != ABSENT && ld(c, a as usize * 8) <= ld(c, b as usize * 8))
268:                 };
269:                 let index_at = if take_left {
270:                     let at = src + left * 8;
271:                     left += 1;
272:                     at
273:                 } else {
274:                     let at = src + right * 8;
275:                     right += 1;
276:                     at
277:                 };
278:                 c.copy_within(index_at..index_at + 8, dst + out * 8);
279:                 #[cfg(test)]
280:                 SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
281:             }
282:             base = end;
283:         }
284:         std::mem::swap(&mut src, &mut dst);
285:         width *= 2;
286:     }
287: }
```

```text
306: fn semantic(
307:     b: &mut [u8],
308:     c: &mut Candidate2048,
309:     loan: &Loan<'_>,
310:     p: &Progress,
311:     steps: &mut StepBudget,
312: ) -> SemanticReply {
313:     // G128 owns these zero-debit terminal paths. Scratch remains untouched.
314:     if b.len() != ARENA_BYTES || steps.spent != 0 {
315:         return poison(0);
316:     }
317:     if steps.remaining < SEMANTIC_RECORD {
318:         return SemanticReply {
319:             status: 2,
320:             reason: 1,
321:             debit: 0,
322:         };
323:     }
324:     steps.remaining -= SEMANTIC_RECORD;
325:     steps.spent = SEMANTIC_RECORD;
326:     let w = loan.record.words;
327:     let f = loan.config;
328:     if f.slots == 0
329:         || f.slots > 64
330:         || f.pins == 0
331:         || f.pins > 64
332:         || p.terminal() != 0
333:         || p.latch >> 8 > f.pins
334:         || p.q[3] > 10
335:     {
336:         return poison(SEMANTIC_RECORD);
337:     }
338:     if w[1] == 14 {
339:         return reject(14);
340:     }
```

```text
625:             }
626:             let slot = if w[13] == 0 { cq(c, 17) } else { p.q[14] };
627:             if slot >= f.slots || w[10] != slot {
628:                 return reject(7);
629:             }
630:             let slot = slot as usize;
631:             if w[13] == 0 {
632:                 if rr(b, slot, 0) != 1 || rr(b, slot, 1) != w[6] || rr(b, slot, 2) != w[14] {
633:                     return reject(7);
634:                 }
635:                 c[1536..1600]
636:                     .copy_from_slice(&b[RESIDENT.base + slot * 64..RESIDENT.base + slot * 64 + 64]);
637:             } else {
638:                 if p.q[15] != 1 || p.q[10] != p.q[12] || rr(b, slot, 0) != 0 || w[14] != cq(c, 18) {
639:                     return reject(9);
640:                 }
641:                 // Reserved tail is zero by Candidate construction/cleanup induction.
642:                 c.copy_within(1944..2008, 1536);
643:                 st(c, 1536, 1);
644:                 st(c, 1544, w[6]);
645:                 st(c, 1552, w[14]);
646:                 st(c, 1576, w[3]);
647:                 sq(c, 6, count + 1);
648:                 let Some(sum) = total.checked_add(w[14]) else {
649:                     return reject(10);
650:                 };
651:                 sq(c, 7, sum);
652:             }
653:             let prior_pins = ld(c, 1560);
654:             let Some(pins) = prior_pins.checked_add(1) else {
655:                 return reject(11);
656:             };
657:             if w[15] != pins || pins > f.pins || p.q[8] == f.pins {
658:                 return reject(11);
659:             }
660:             st(c, 1560, pins);
661:             st(c, 1568, w[4]);
662:             st(c, 1600, slot as u64);
663:             st(c, 1608, w[12]);
664:             st(c, 1616, w[3]);
665:             st(c, 1624, w[3]);
666:             st(c, 1632, w[4]);
667:             st(c, 1640, w[5]);
668:             resident_delta = slot as u64;
669:             pin_delta = first_pin;
670:             sq(c, 8, p.q[8] + 1);
671:             sq(c, 9, p.q[9] + 1);
672:         }
673:         12 => {
674:             let slot = w[10] as usize;
675:             let pin = w[11] as usize;
676:             if slot >= f.slots as usize
677:                 || pin >= f.pins as usize
678:                 || pr(b, pin, 0) != w[10]
679:                 || pr(b, pin, 1) != w[12]
680:             {
681:                 return reject(11);
682:             }
683:             if rr(b, slot, 0) != 1
684:                 || rr(b, slot, 1) != w[6]
685:                 || rr(b, slot, 2) != w[13]
686:                 || rr(b, slot, 3) == 0
687:                 || p.q[8] == 0
688:                 || w[15] != rr(b, slot, 3) - 1
689:             {
690:                 return reject(11);
691:             }
692:             c[1536..1600]
693:                 .copy_from_slice(&b[RESIDENT.base + slot * 64..RESIDENT.base + slot * 64 + 64]);
694:             st(c, 1560, w[15]);
695:             for i in 0..6 {
696:                 st(c, 1600 + i * 8, if i == 0 { ABSENT } else { 0 });
697:             }
698:             resident_delta = w[10];
699:             pin_delta = w[11];
700:             sq(c, 8, p.q[8] - 1);
701:         }
702:         13 => {}
703:         _ => return poison(SEMANTIC_RECORD),
704:     }
705:     // Mirror only the already audited envelope successor. Semantic reply itself
706:     // is installed by the caller after cleanup; refusal never installs scratch.
707:     sq(c, 0, w[0]);
708:     sq(c, 1, w[4]);
709:     sq(c, 2, w[5]);
710:     let stage = match w[1] {
711:         1 => 1,
712:         2 => {
713:             if w[13] == 1 {
714:                 2
715:             } else {
716:                 3
717:             }
718:         }
719:         3 => 4,
720:         4 => 5,
721:         5 | 8 => 6,
722:         6 => 7,
723:         7 => 8,
724:         9 => 9,
725:         10 => 10,
726:         _ => 0,
727:     };
728:     sq(c, 3, stage);
729:     sq(c, 4, if stage == 0 { 0 } else { w[3] });
730:     sq(c, 5, if stage == 0 { ABSENT } else { w[6] });
731:     // Every destination and fixed width was established by exact arena length,
732:     // validated rows, constant cell indices and the candidate's array type.
733:     // No callback, allocation, Result or fallible range follows first mutation.
734:     if resident_delta != ABSENT {
735:         let at = RESIDENT.base + resident_delta as usize * 64;
736:         b[at..at + 64].copy_from_slice(&c[1536..1600]);
737:         if !commit_succeeded() {
738:             return SemanticReply {
739:                 status: 3,
740:                 reason: 16,
741:                 debit: SEMANTIC_RECORD,
742:             };
743:         }
744:     }
745:     if pin_delta != ABSENT {
746:         let at = PIN.base + pin_delta as usize * 48;
747:         b[at..at + 48].copy_from_slice(&c[1600..1648]);
748:     }
749:     if plan_delta != ABSENT {
750:         let at = PLAN.base + plan_delta as usize * 40;
751:         b[at..at + 40].copy_from_slice(&c[1648..1688]);
752:     }
753:     for i in 0..10 {
754:         let source = SC + (6 + i) * 8;
755:         let destination = SCALAR.base + ROW_CELLS[i] * 8;
756:         b[destination..destination + 8].copy_from_slice(&c[source..source + 8]);
757:     }
758:     for i in 0..2 {
759:         let source = SC + (17 + i) * 8;
760:         let destination = SCALAR.base + EXTRA_CELLS[i] * 8;
761:         b[destination..destination + 8].copy_from_slice(&c[source..source + 8]);
762:     }
763:     if w[1] == 6 {
764:         st(b, SCALAR.base + 138 * 8, w[13]);
765:     }
766:     SemanticReply {
767:         status: 1,
768:         reason: 0,
769:         debit: SEMANTIC_RECORD,
770:     }
771: }
772: // This sole cleanup block follows every loan return. Length/ranges are checked
773: // before the loan and the exact same exclusive slice survives through here.
774: // Explicit zero-word stores avoid a second2048-byte temporary source owner.
775: fn cleanup(b: &[u8], c: &mut Candidate2048) -> bool {
776:     if b.len() != ARENA_BYTES {
777:         return false;
778:     }
779:     let zero = [0u8; 8];
780:     for i in 0..256 {
781:         let at = i * 8;
782:         c[at..at + 8].copy_from_slice(&zero);
783:     }
784:     for i in 0..12 {
785:         let source = SCALAR.base + CELLS[i] * 8;
786:         let destination = 888 + i * 8;
787:         // Both cells already encode one canonical LE u64: this complete8-byte
788:         // load/restore needs no scalar decode/re-encode or array return place.
789:         c[destination..destination + 8].copy_from_slice(&b[source..source + 8]);
790:     }
791:     #[cfg(test)]
792:     if CLEANUP_FAULT.swap(false, std::sync::atomic::Ordering::Relaxed) {
793:         c[0] = 0x51;
794:         return false;
795:     }
796:     true
797: }
```

```text
901: fn projection(
902:     p: &Progress,
903:     paid: &Paid,
904:     s: &Framing,
905:     input: &Result<bool, AnalyzerError>,
906:     env: &FixtureEnvelopeObservationV1,
907:     f: Option<&Fixture>,
908: ) -> FixtureCacheStateObservationV1 {
909:     use FixtureCacheStateBoundaryV1 as B;
910:     let mut z = FixtureCacheStateObservationV1 {
911:         boundary: B::Unavailable,
912:         reason: why(5),
913:         extent: [0; 30],
914:     };
915:     z.extent[19] = 512 * paid.setup + 256 * paid.finish + 7680 * paid.records;
916:     z.extent[20] = paid.setup;
917:     z.extent[21] = paid.finish;
918:     // Ordered T01..T09. T00 is exclusively the actual outer Result path.
```

```text
1072: fn cache_walk<T: InputFile>(
1073:     input: &mut T,
1074:     arena: &mut Arena,
1075:     budget: &mut Budget,
1076:     f: &Fixture,
1077:     length: u64,
1078:     s: &mut Framing,
1079:     e: &mut FixtureEnvelopeProgressV1,
1080:     p: &mut Progress,
1081:     paid: &mut Paid,
1082: ) -> Result<(), AnalyzerError> {
1083:     let mut reader = Reader::new(length, HEADER_STAGE);
1084:     let mut h = [0; 64];
1085:     reader.words(input, arena, budget, &mut h)?;
1086:     header(arena, &h, *f, budget)?;
1087:     budget.setup(SETUP_ENVELOPE)?;
1088:     e.debit += SETUP_ENVELOPE;
1089:     budget.report(FINISH_ENVELOPE)?;
1090:     e.debit += FINISH_ENVELOPE;
1091:     budget.report(UNDERFUNDED_GUARD)?;
1092:     budget.report(SEMANTIC_GUARD)?;
1093:     if arena.bytes.len() != ARENA_BYTES {
1094:         return Err(error(INTERNAL, ARENA_STAGE, 0, 0));
1095:     }
1096:     // The sole Candidate is constructed only after all guards are reserved.
1097:     let mut candidate: Candidate2048 = [0; 2048];
1098:     for i in 0..12 {
1099:         let at = SCALAR.base + CELLS[i] * 8;
1100:         st(
1101:             &mut arena.bytes,
1102:             at,
1103:             if i == 5 {
1104:                 1
1105:             } else if i == 6 {
1106:                 f.mask
1107:             } else {
1108:                 0
1109:             },
1110:         );
1111:     }
1112:     p.q[5] = ABSENT;
1113:     p.q[9] = 1;
1114:     p.q[13] = ABSENT;
1115:     p.q[14] = ABSENT;
1116:     st(&mut arena.bytes, SCALAR.base + 17 * 8, 1);
```

```text
1159:             if p.terminal() == 0 && e.reply.words[0] == 1 && e.reply.words[1] == 0 {
1160:                 // Before loan, exact exclusive arena length proves every region
1161:                 // and all12restore ranges. No scratch access precedes this check.
1162:                 if arena.bytes.len() != ARENA_BYTES {
1163:                     p.latch_terminal(16);
1164:                 } else {
1165:                     let loan = Loan {
1166:                         record: &record,
1167:                         config: f,
1168:                     };
1169:                     let mut semantic_steps = StepBudget {
1170:                         remaining: SEMANTIC_RECORD,
1171:                         spent: 0,
1172:                     };
1173:                     #[cfg(test)]
1174:                     SEMANTIC_CALLS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
1175:                     let received = semantic(
1176:                         &mut arena.bytes,
1177:                         &mut candidate,
1178:                         &loan,
1179:                         p,
1180:                         &mut semantic_steps,
1181:                     );
1182:                     p.calls += 1;
1183:                     // Capture committed fixed snapshot before sole cleanup. The
1184:                     // leaf cannot export a partially staged successor on refusal.
1185:                     if received.status == 1
1186:                         && received.reason == 0
1187:                         && received.debit == SEMANTIC_RECORD
1188:                         && semantic_steps.spent == SEMANTIC_RECORD
1189:                         && semantic_steps.remaining == 0
1190:                     {
1191:                         for i in 0..16 {
1192:                             p.q[i] = cq(&candidate, i);
1193:                         }
1194:                         p.remember_pin(cq(&candidate, 16));
1195:                     } else if received.status == 2
1196:                         && (received.reason == 1 || (6..=14).contains(&received.reason))
1197:                         && ((received.debit == SEMANTIC_RECORD
1198:                             && semantic_steps.spent == SEMANTIC_RECORD
1199:                             && semantic_steps.remaining == 0)
1200:                             || (received.reason == 1
1201:                                 && received.debit == 0
1202:                                 && semantic_steps.spent == 0
1203:                                 && semantic_steps.remaining < SEMANTIC_RECORD))
1204:                     {
1205:                         p.latch_terminal(received.reason);
1206:                     } else {
1207:                         p.latch_terminal(16);
1208:                     }
1209:                     if !cleanup(&arena.bytes, &mut candidate) {
1210:                         p.latch_terminal(16);
1211:                     }
1212:                 }
1213:             }
1214:         }
```

```text
1251: fn cache_inputs<S: InputFile, P: InputFile, C: InputFile>(
1252:     stream: &mut S,
1253:     profile_file: &mut P,
1254:     context: &mut C,
1255:     arena: &mut Arena,
1256:     budget: &mut Budget,
1257:     s: &mut Framing,
1258:     e: &mut FixtureEnvelopeProgressV1,
1259:     p: &mut Progress,
1260:     paid: &mut Paid,
1261:     config: &mut Option<Fixture>,
1262: ) -> Result<bool, AnalyzerError> {
1263:     let before_s = initial(stream, budget)?;
1264:     let before_p = initial(profile_file, budget)?;
1265:     let before_c = initial(context, budget)?;
1266:     if before_s.len() < 1024
1267:         || before_s.len() > STREAM_CAP
1268:         || (before_s.len() - 1024) % 128 != 0
1269:         || before_p.len() != PROFILE_BYTES
1270:         || before_c.len() != CONTEXT_BYTES
1271:     {
1272:         return Err(error(INPUT, ADMISSION_STAGE, 0, 0));
1273:     }
1274:     s.physical = (before_s.len() - 1024) / 128;
1275:     let f = fixture_context(context, arena, budget)?;
1276:     profile(profile_file, arena, budget, f)?;
1277:     *config = Some(f);
1278:     cache_walk(stream, arena, budget, &f, before_s.len(), s, e, p, paid)?;
1279:     stable(stream, before_s, budget)?;
1280:     stable(profile_file, before_p, budget)?;
1281:     stable(context, before_c, budget)?;
1282:     Ok(s.complete)
1283: }
1284: macro_rules! cache_body {
1285:     ($input_s:ident,$input_p:ident,$input_c:ident,$output_f:ident,$limit:expr) => {{
1286:         let stream = $input_s;
1287:         let profile_file = $input_p;
1288:         let context = $input_c;
1289:         let output = $output_f;
1290:         let limit = $limit;
1291:         let mut budget = Budget::new(limit)?;
1292:         budget.setup(SETUP_WRAPPER)?;
1293:         budget.report(FINAL_WRAPPER)?;
1294:         // SF then SS must both succeed before *any* new semantic aggregate/progress
1295:         // owner exists. The only eventual Ok is below these two propagating calls.
1296:         budget.report(SEMANTIC_FINISH)?;
1297:         budget.setup(SEMANTIC_SETUP)?;
1298:         let mut paid = Paid {
1299:             setup: 1,
1300:             finish: 1,
1301:             records: 0,
1302:         };
1303:         let output_initial = output_safety(stream, profile_file, context, output, &mut budget)?;
1304:         let mut arena = Arena::new(&mut budget)?;
1305:         let mut s = Framing::new(0);
1306:         let mut e = FixtureEnvelopeProgressV1 {
1307:             reply_valid: 0,
1308:             debit: 0,
1309:             reply: FixtureEnvelopeReplyV1 { words: [0; 16] },
1310:         };
1311:         let mut p = Progress {
1312:             calls: 0,
1313:             latch: 0,
1314:             q: [0; 16],
1315:         };
1316:         let mut config = None;
1317:         let result = cache_inputs(
1318:             stream,
1319:             profile_file,
1320:             context,
1321:             &mut arena,
1322:             &mut budget,
1323:             &mut s,
1324:             &mut e,
1325:             &mut p,
1326:             &mut paid,
1327:             &mut config,
1328:         );
1329:         let mut observation = error(BINDING, CONTEXT_STAGE, 0, 0);
1330:         let mut decision = Decision::Unavailable;
1331:         let mut framed = false;
1332:         if let Err(err) = result {
1333:             observation = err;
1334:             decision = if err.code == BINDING {
1335:                 Decision::Unavailable
1336:             } else if err.code == BUDGET {
1337:                 Decision::AnalysisLimited
1338:             } else {
1339:                 Decision::Invalid
1340:             };
1341:         } else if s.limited {
1342:             observation = error(BUDGET, RECORD_STAGE, 512 + s.framed * 128, s.framed + 1);
1343:             decision = Decision::AnalysisLimited;
1344:         } else {
1345:             framed = result.unwrap_or(false);
1346:         }
1347:         let envelope = finalize(&e, &s, &result, &arena);
1348:         let cache_state = projection(&p, &paid, &s, &result, &envelope, config.as_ref());
1349:         let mut framing = ReplayOutcome {
1350:             decision,
1351:             framed_records: s.framed,
1352:             physical_records: s.physical,
1353:             report_bytes: 0,
1354:             steps_used: 0,
1355:             input_bytes_read: budget.read_bytes,
1356:             input_attempts: budget.io_spent,
1357:             output_attempts: 0,
1358:             observation,
1359:             fixture_framing: u64::from(framed),
1360:         };
1361:         write_report(
1362:             output,
1363:             output_initial,
1364:             &mut arena,
1365:             &mut budget,
1366:             &mut framing,
1367:             s,
1368:         )?;
1369:         if budget.used() > budget.limit {
1370:             return Err(error(BUDGET, OUTPUT_STAGE, 0, 0));
1371:         }
1372:         Ok(FixtureCacheStateOutcomeV1 {
1373:             framing,
1374:             envelope,
1375:             cache_state,
1376:         })
1377:     }};
1378: }
1379: #[cfg(test)]
1380: fn cache_core<S: InputFile, P: InputFile, C: InputFile, O: OutputFile>(
1381:     stream: &mut S,
1382:     profile_file: &mut P,
1383:     context: &mut C,
1384:     output: &mut O,
1385:     limit: u64,
1386: ) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError> {
1387:     cache_body!(stream, profile_file, context, output, limit)
1388: }
1389: /// Four distinct, quiescent regular Files at offset0; empty exclusive output.
1390: /// Only parsed synthetic MIXFIX01/MIXPRF01 identity is observed.
1391: pub fn analyze_fixture_cache_state_v1(
1392:     stream: &mut File,
1393:     profile_file: &mut File,
1394:     context: &mut File,
1395:     output: &mut File,
1396: ) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError> {
1397:     cache_body!(stream, profile_file, context, output, STEP_LIMIT)
1398: }
```

## verification/swift-cache-state-implementation/correction-1/source/library/analyzer.rs

```text
27: const REPORT_MAGIC: u64 = u64::from_le_bytes(*b"MIXANL01");
28: 
29: /// Fixed failure observation. No error text, original-result substitution or heap owner.
30: #[derive(Clone, Copy, Debug, PartialEq, Eq)]
31: #[repr(C)]
32: pub struct AnalyzerError { pub code: u32, pub stage: u32, pub offset: u64, pub record: u64, pub reserved: u64 }
33: fn error(code: u32, stage: u32, offset: u64, record: u64) -> AnalyzerError {
34:     AnalyzerError { code, stage, offset, record, reserved: 0 }
35: }
```

```text
68: pub struct ReplayOutcome {
69:     pub decision: Decision,
70:     /// Closed syntactic framing count; never an accepted semantic record count.
71:     pub framed_records: u64,
72:     pub physical_records: u64,
73:     pub report_bytes: u64,
74:     pub steps_used: u64,
75:     pub input_bytes_read: u64,
76:     pub input_attempts: u64,
77:     pub output_attempts: u64,
78:     pub observation: AnalyzerError,
79:     fixture_framing: u64,
80: }
81: impl ReplayOutcome {
82:     pub const fn fixture_framing_observed(&self) -> bool { self.fixture_framing == 1 }
83:     pub const fn stored_prefix_validated(&self) -> bool { false }
84:     pub const fn full_replay_accepted(&self) -> bool { false }
85: }
86: 
87: #[derive(Clone, Copy)]
88: struct Region { base: usize, rows: usize, stride: usize }
89: const FUNCTION: Region = Region { base: 0, rows: 80_000, stride: 96 };
90: const RESIDENT: Region = Region { base: 7_680_000, rows: 64, stride: 64 };
91: const PIN: Region = Region { base: 7_684_096, rows: 64, stride: 48 };
92: const PLAN: Region = Region { base: 7_687_168, rows: 512, stride: 40 };
93: const RECENCY: Region = Region { base: 7_707_648, rows: 64, stride: 8 };
94: const WINDOW: Region = Region { base: 7_708_160, rows: 128, stride: 128 };
95: const HISTOGRAM: Region = Region { base: 7_724_544, rows: 396, stride: 8 };
96: const TOP: Region = Region { base: 7_727_712, rows: 32, stride: 64 };
97: const SCALAR: Region = Region { base: 7_729_760, rows: 512, stride: 8 };
98: const CONTEXT: Region = Region { base: 7_733_856, rows: 1024, stride: 8 };
99: const BLOCK: Region = Region { base: 7_742_048, rows: 1, stride: 65_536 };
100: const REPORT: Region = Region { base: 7_807_584, rows: 8192, stride: 8 };
101: const REGIONS: [Region; 12] = [FUNCTION, RESIDENT, PIN, PLAN, RECENCY, WINDOW, HISTOGRAM, TOP, SCALAR, CONTEXT, BLOCK, REPORT];
102: 
103: struct Arena { bytes: Vec<u8> }
104: impl Arena {
105:     fn new(budget: &mut Budget) -> Result<Self, AnalyzerError> {
```

```text
257:     }
258: }
259: 
260: #[derive(Clone, Copy)]
261: struct Fixture { cap: u64, mask: u64, extent: u64, types: u64, slots: u64, pins: u64, base: u64, capacity: u64, entry: u64 }
262: fn fixture_context<T: InputFile>(input: &mut T, arena: &mut Arena, budget: &mut Budget) -> Result<Fixture, AnalyzerError> {
263:     let mut reader = Reader::new(CONTEXT_BYTES, CONTEXT_STAGE);
```

## verification/swift-cache-state-implementation/correction-1/source/library/envelope.rs

```text
1: //! Separate safe-File fixture envelope. No replay, binding or release authority.
2: use super::*;
3: 
4: const SETUP_ENVELOPE: u64 = 534;
5: const FINISH_ENVELOPE: u64 = 47;
6: const RECORD_ENVELOPE: u64 = 425;
7: const SETUP_WRAPPER: u64 = 42;
8: const FINAL_WRAPPER: u64 = 42;
9: const UNDERFUNDED_GUARD: u64 = 112;
10: // Selected operation-ledger partition W01..W09; outer F42 includes early-error13.
11: const WRAPPER_GROUPS: [u64; 9] = [1, 3, 1, 2, 3, 2, 1, 5, 6];
12: const WRAPPER_STEPS: u64 = WRAPPER_GROUPS[0] + WRAPPER_GROUPS[1] + WRAPPER_GROUPS[2] + WRAPPER_GROUPS[3]
13:     + WRAPPER_GROUPS[4] + WRAPPER_GROUPS[5] + WRAPPER_GROUPS[6] + WRAPPER_GROUPS[7]
14:     + WRAPPER_GROUPS[8];
15: const COMBINED_RECORD: u64 = RECORD_STEPS + RECORD_ENVELOPE + WRAPPER_STEPS;
16: const CELLS: [usize; 12] = [7, 9, 10, 11, 12, 13, 14, 64, 65, 66, 160, 161];
17: const PAYLOAD: usize = 888;
18: type Candidate2048 = [u8; 2048];
19: const _: () = assert!(COMBINED_RECORD <= RECORD_PREFLIGHT && SCALAR.base + 161 * 8 + 8 <= ARENA_BYTES && PAYLOAD + 12 * 8 <= 2048);
20: 
```

```text
77: }
78: 
79: #[repr(C)]
80: struct StepBudget { remaining: u64, spent: u64 }
81: #[repr(C)]
82: struct CheckedPair { status: u64, value: u64 }
83: #[repr(C)]
84: struct FixtureEnvelopeReplyV1 { words: [u64; 16] }
85: #[repr(C)]
86: struct FixtureEnvelopeProgressV1 {
```

## Accepted definition: docs/swift-semantic-adapter-prerequisite.md

```text
219: return, clear the scratch **in place** and restore candidate bytes888..983 from
220: the envelope's12 arena scalar cells7,9,10,11,12,13,14,64,65,66,160,161. The next envelope call
221: therefore receives its exact previous payload and zero nonpayload bytes. No
222: fresh `[0;2048]` source/destination pair is created each record. All clear,
223: restore, borrow and transfer work must be included below.
224: 
225: The new walker proves the full arena length and all12 restore ranges before
226: granting the private semantic loan. The same exclusive, non-resizable arena
227: slice survives through the leaf and cleanup, and semantic writes are disjoint
228: from those12 envelope cells. Every ordinary success/refusal/private Error reply
229: returns to one cleanup block before any next leaf dispatch; it cannot use `?`
230: or another outer return that bypasses cleanup. Cleanup has no callback,
231: allocation, fallible conversion or unproved range after the first clear store.
232: The source ledger must account for all256 in-place zero-word iterations,
233: 12 complete scalar loads and restores, their loop/borrow/copy/return work and
234: every source/destination place. No2048-byte zero initializer is hidden in a
235: helper argument. An outer read/footer/drift/output Error occurs only with the
236: candidate already clean/restored; pre-candidate setup Error has no such owner.
237: If private readability/ownership proof fails before a loan, the guard does not
238: touch scratch. An unexpected commit/cleanup fault latches poison, suppresses
239: extent and disables **both** later leaf dispatches, so no damaged candidate is
240: reused; only bounded framing/drain/finalization may continue. A failure cannot
241: claim successful restoration when the proof was unavailable. These paths are
242: mandatory independent controls, not exception-based cleanup assumptions.
243: 
244: Global ceilings stay arena8,388,608, complete named transients65,536,
245: reserved transients41,984, authored steps268,435,456, setup65,536,
246: report3,000,000, I/O263,584, next-record preflight8,192,
247: Rust report49,152 and aggregate report65,536. The proposed new-path ceilings are:
248: 
249: | Proposed semantic per-record group | Maximum authored debits |
250: | --- | ---: |
251: | admission, prior controls and record loan | 256 |
252: | up to64 resident probes plus64 token probes and scratch seeding | 2,560 |
253: | up to321 stable merge comparisons,8 each | 2,568 |
254: | up to384 index transfers,2 each | 768 |
255: | up to64 selected-prefix arithmetic steps,10 each | 640 |
256: | complete delta staging/commit plus candidate clear/restore | 640 |
257: | complete reply/received/progress transfers, audit and terminal paths | 248 |
258: | **semantic ceiling per successfully paid combined record** | **7,680** |
259: 
260: These are **proposed admissible source-work ceilings**, not a verified ledger
261: for missing Rust. Each micro-operation, loop guard, fixed copy, little-endian
262: conversion, full Result and caller move must map exactly once to a ledger row;
263: scalar blocks use at most16 named operations/group and copies at most128 bytes/
264: group. Group maxima are not interchangeable spare credits. Missing or
265: over-budget mapping blocks implementation acceptance; it never increases a cap.
266: No implicit optimizer elision supplies the bound.
267: 
268: The inherited combined framing/envelope/wrapper record charge stays471 on old
269: paths. The new path prepays exactly471+7,680 = **8,151**, only after unchanged
270: 8,192 preflight, leaving41. Charge the full amount even if a later read or
271: framing check refuses, semantic dispatch is already latched or a later footer
272: invalidates observations. The old public envelope debit remains exactly
273: `534*S_paid + 47*F_paid + 425*N_B`. New public fixture semantic debit is exactly
274: `512*SS_paid + 256*SF_paid + 7680*N_C`; N_C counts successful new combined
275: charges, not leaf invocations or valid records. No refund or double counting.
276: 
277: Proposed extra semantic setup512 reserves fixed scalar initialization/views and
278: all new wrapper source/destination work. It reuses the already initialized
279: Candidate2048. Extra finish256 reserves projection, complete aggregate/Result/
280: caller moves and early-error finalization. A separately reserved terminal
281: guard128 covers one absent/readability/invalid-private-budget/underfunded leaf;
282: it latches immediately and cannot be reused. Old G112 retains its existing
283: envelope ownership. The report reserve must fund old6,446 +new256+128 =6,830;
284: actual per-source finalization and zero-call paths still require review. Existing
285: setup allowance must be checked against the **entire** new setup, including
286: profile/context/setup failures, rather than only512. Reserved I/O funding and
287: drain/EOF limits remain unchanged. No semantic tail runs after a budget stop.
288: 
289: Proposed reservation order is the existing Budget/T42/F42 boundary, then new
290: finish256 **before** any new semantic Progress/observation/aggregate owner,
291: then new setup512. If new finish admission fails, only the existing funded
292: fixed AnalyzerError path may return; no new aggregate is constructed. Setup
293: failure preserves whichever reservations actually succeeded. After actual
294: context/profile/header admission, reserve the unchanged envelope setup534,
295: finish47/G112 and new terminal guard128 before candidate/scalar mutation.
296: No guard or inactive branch funds an otherwise unpaid early return. Every
297: one of these proposed amounts and declaration sizes remains provisional until
298: actual Rust source, complete caller/Result lifetimes and fresh layouts are
299: independently reconciled.
300: 
301: The conservative historical fixed non-record allowance in `contract.json`
302: leaves an arithmetic maximum of32,317 paid8,151 records under the global cap.
303: That is an upper bound, not a complete historical replay promise; actual
304: setup/I/O/refusal can stop earlier. The original2,889,656-record arithmetic
305: envelope would exceed this cap by a wide margin. This source-only prerequisite
306: is useful through finite fixtures and makes no claim to consume it in full.
307: 
308: Keep all existing complete24656-byte storage roles. Proposed additional roles
309: are control1,280 (within control8,192's prior6,656), wire256 (within wire3,072's
310: prior2,616), report2,896 (within report8,192's prior4,296) and setup256 (within
311: setup12,288's prior5,168). Total proposed complete union29,344 <41,984; no
312: 23,552 unassigned global margin is spent. Candidate remains exactly2,048.
313: Control covers private Progress144, both complete reply/received128 places,
314: record/config/arena/candidate/budget borrows, loop/prior/helper/Option/Pair
315: places and errors. Report covers observation source+destination512, aggregate
316: source+destination976, complete Result source+caller1,024, projection256 and
317: error128. Union is a conservative named-role bound, not simultaneous stack/RSS.
318: The future ledger must locate every source/destination, its lexical phase and
319: drop boundary, including error paths; no by-value loan/candidate/array move or
320: missing caller Result may be ignored. Fresh size/layout evidence is mandatory.
```
