from pathlib import Path
p=Path(__file__).resolve().parent/'source/src/experimental_swift_reactor/cache.rs'
s=p.read_text().replace('                    plans: &mut self.plans,\n                    plans: &mut self.plans,','                    plans: &mut self.plans,').replace('                plans: &mut cache.plans,\n                    plans: &mut cache.plans,','                    plans: &mut cache.plans,')
p.write_text(s)
