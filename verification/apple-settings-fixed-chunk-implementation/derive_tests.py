"""Adapt retained host controls to direct receiver dispatch; never open sockets."""
import ast,pathlib
B=pathlib.Path(__file__).resolve().parent

def remove_methods(source,names):
 tree=ast.parse(source);lines=source.splitlines(keepends=True)
 spans=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.FunctionDef) and node.name in names:spans.append((node.lineno-1,node.end_lineno))
 assert len(spans)==len(names),(spans,names)
 for start,end in sorted(spans,reverse=True):lines[start:end]=[]
 return ''.join(lines)

s=(B/'fixture-inputs/fixtures.py').read_text()
start=s.index('HERE = ');end=s.index('\n\ndef image():')
s=s[:start]+'''HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTED = HERE/'sources/selected'
V9 = SELECTED/'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation'
sys.path.insert(0,str(V9))
import settings_telemetry as t
import replay
import types
class DirectBase:
    """Minimal base adapter; not an HTTP, framing, capability or app-origin test."""
    def __init__(self, documents, output, capability, identity, **kwargs):
        self.output=output;output.mkdir(parents=True)
        self.capability=capability;self.identity=identity;self.current=None;self.generation=0
        self.deadline=500.0;self.failures=[]
    def persist_summary(self):pass
    def record_failure(self, op, error):self.failures.append({'operation':op,'reason':str(error)})
    def _request(self, op, body):raise ValueError('Unsupported test adapter operation')

def strict_summary(scope,bridge,*args):
    s=bridge.settings.summary()
    ready=(s['setupObservationSatisfied'] and s['terminationMarkers']==['terminate-before','terminate-after']
           and s['completionMarkers']==['test-case-finished','suite-finished','bundle-finished']
           and not s['persistenceRetirementPending'] and not s['persistenceUncertain'])
    return dict(diagnosticCompleted=ready,setupEvidenceComplete=ready,dependentCasesUnrun=list(range(6)),
        persistenceRetirement=bridge.persistence.retirement,nativeKeyboardQualification=False,carrierAccepted=False,
        gaAccepted=False,runPassed=False,strictNativeVerdictsPassed=False)
producer=types.SimpleNamespace(h=types.SimpleNamespace(Bridge=t.diagnostic_bridge(DirectBase)),keyboard_oracle=types.SimpleNamespace(CASES=set()),summary=strict_summary)
SCRATCH=HERE/'synthetic-attempts'
SCRATCH.mkdir(exist_ok=True)
''' +s[end:]
s=s.replace("'uptime': self.runner})","'uptime': self.runner, 'chunkBytes': 4992})")
s=s.replace('real-v9-','fixed4992-')
(B/'fixtures.py').write_text(s)
s=(B/'fixture-inputs/test_v9.py').read_text()
s=remove_methods(s,{'test_actual_http_rejects_boolean_query_count_no_durable_advance','test_frozen_v6_journal_exact_failure_and_corrected_route_credit_still_off','test_actual_compiled_swift_resolver_wire_passes_actual_host_validator'})
s=s.replace('(3072,7000000,2500,100,32,29.0)','(4992,7000000,2500,100,32,29.0)')
(B/'test_retained_proof.py').write_text(s)
s=(B/'fixture-inputs/test_persistence.py').read_text();start=s.index('def send_http(');end=s.index('\n\nclass FaultIO',start)
s=s[:start]+'''def send_direct(flow, record):
    """In-process adapter status; no real HTTP or listener is exercised."""
    try:return 200,flow.send(record)
    except (ValueError,OSError) as error:return 400,{'error':type(error).__name__+': '+str(error)}
'''+s[end:]
s=s.replace('import http.client\n','').replace('import threading\n','')
s=s.replace('send_http','send_direct').replace('real loopback HTTP','in-process direct dispatch').replace('HTTP','adapter').replace('http','adapterStatus')
(B/'test_retained_persistence.py').write_text(s)
print('Derived direct-dispatch controls; 3 historical/network-only V9 tests excluded explicitly.')
