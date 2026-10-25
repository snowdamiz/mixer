"""Exact copied-source transforms; never mutate the live VM."""
from pathlib import Path
import json
HERE = Path(__file__).resolve().parent
def transform(name, data):
    text = data.decode()
    def replace(old, new, count=1):
        nonlocal text
        assert text.count(old) == count, (name, old, text.count(old))
        text = text.replace(old, new)
    def before(old, inserted):
        replace(old, inserted + old)
    if name == 'src/experimental/cache/borrowed.rs':
        before('    fn step(&mut self, _: CacheStep) {}', '''    #[cfg(test)]
    fn diagnostic_site(&mut self, _: u8) {}
    #[cfg(test)]
    fn diagnostic_lookup_done(&mut self, _: bool) {}
    #[cfg(test)]
    fn diagnostic_decode_completed(&mut self, _: u32) {}
''')
        before('    meter.step(CacheStep::Lookup);', '    #[cfg(test)]\n    meter.diagnostic_site(1);\n')
        before('    for (index, record) in parts.pins.iter().enumerate() {', '    #[cfg(test)]\n    meter.diagnostic_site(2);\n')
        replace('    let mut hit = None;\n    for (index, slot) in parts.slots.iter().enumerate() {', '    let mut hit = None;\n    #[cfg(test)]\n    meter.diagnostic_site(3);\n    for (index, slot) in parts.slots.iter().enumerate() {')
        replace('        meter.usage_mut().hit(hits);', '        meter.usage_mut().hit(hits);\n        #[cfg(test)]\n        meter.diagnostic_lookup_done(true);')
        replace('        meter.usage_mut().miss(misses);', '        meter.usage_mut().miss(misses);\n        #[cfg(test)]\n        meter.diagnostic_lookup_done(false);')
        before('        meter.work(parts.slots.len() as u64)?;', '        #[cfg(test)]\n        meter.diagnostic_site(6);\n')
        before('        while empty.is_none() || base + remaining + bytes > capacity {', '        #[cfg(test)]\n        meter.diagnostic_site(7);\n')
        before('        meter.work(MAX_ENTRIES as u64)?;', '        #[cfg(test)]\n        meter.diagnostic_site(8);\n')
        before('        meter.step(CacheStep::Publication);', '        #[cfg(test)]\n        meter.diagnostic_site(11);\n')
        replace('        meter.usage_mut().decoded(next_decodes, bytes);', '        meter.usage_mut().decoded(next_decodes, bytes);\n        #[cfg(test)]\n        meter.diagnostic_decode_completed(function);')
    elif name == 'src/experimental_swift_reactor/cache.rs':
        replace('''        self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation())''', '''        let result = self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation());
        #[cfg(test)]
        super::cache_tests::attribution_work(n, self.cursor, &result);
        result''')
        before('        test_step(CacheStep::Constructor);', '        #[cfg(test)]\n        super::cache_tests::attribution_site(0);\n')
        before('impl DecodeMeter for SwiftMeter', '')
        replace('''impl DecodeMeter for SwiftMeter<'_, '_> {
    type Failure''', '''impl DecodeMeter for SwiftMeter<'_, '_> {
    #[cfg(test)]
    fn diagnostic_site(&mut self, site: u8) { super::cache_tests::attribution_site(site); }
    #[cfg(test)]
    fn diagnostic_lookup_done(&mut self, hit: bool) { super::cache_tests::attribution_lookup_done(hit); }
    #[cfg(test)]
    fn diagnostic_decode_completed(&mut self, function: u32) { super::cache_tests::attribution_decode_completed(function); }
    type Failure''')
        before('''        operation.cursor = Cursor {
            stage: SwiftRunStage::Cache,''', '        #[cfg(test)]\n        super::cache_tests::attribution_begin(function);\n')
        # Exactly two policy calls: scan first, build_payload second.
        needle='        let policy = policy(snapshot, body, meter)?;'
        assert text.count(needle) == 2
        text=text.replace(needle, '        #[cfg(test)]\n        meter.diagnostic_site(4);\n'+needle, 1)
        at=text.rindex(needle)
        text=text[:at]+'        #[cfg(test)]\n        meter.diagnostic_site(9);\n'+text[at:]
        before('        decode::scan_borrowed(', '        #[cfg(test)]\n        meter.diagnostic_site(5);\n')
        before('        decode::build_borrowed(', '        #[cfg(test)]\n        meter.diagnostic_site(10);\n')
    elif name == 'src/experimental_swift_reactor/cache_tests.rs':
        text += '\n' + (HERE/'observer.rs').read_text() + '\n' + (HERE/'controls.rs').read_text()
    elif name == 'src/experimental_swift_reactor/lifecycle_tests.rs':
        text += '\n// Isolated work attribution harness only.\ninclude!(' + json.dumps(str(HERE/'harness.rs')) + ');\n'
    return text.encode()
