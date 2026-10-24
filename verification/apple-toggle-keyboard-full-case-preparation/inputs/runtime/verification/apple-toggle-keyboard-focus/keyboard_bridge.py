"""Narrow same-endpoint keyboard witness and fixed command-phase adaptation."""
import contextlib
import copy
import time
import keyboard_oracle as o


def keyboard_bridge(base,transport):
    class KeyboardBridge(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.keyboard_cases={}
        @contextlib.contextmanager
        def command_prefix(self,prefix):
            name=self.current['case'];prior=transport.CASE_COMMAND_SEQUENCE[name]
            transport.CASE_COMMAND_SEQUENCE[name]=prefix
            try:yield
            finally:transport.CASE_COMMAND_SEQUENCE[name]=prior
        def _request(self,op,body):
            if op=='begin':
                result=super()._request(op,body)
                cursor=o.Cursor(self.current['case']);self.current['keyboardCursor']=cursor;self.keyboard_cases[cursor.name]=cursor
                return result
            if self.current is None:return super()._request(op,body)
            cursor=self.current['keyboardCursor']
            if op=='command':
                o.require(type(body) is dict and set(body)=={'command'} and body['command']==cursor.next_command(),'Keyboard fixture command outside fixed phase')
                with self.command_prefix(cursor.done_commands+[body['command']]):result=super()._request(op,body)
                cursor.command(body['command']);return result
            if op=='baseline':
                cursor.baseline_allowed()
                with self.command_prefix(cursor.done_commands):result=super()._request(op,body)
                self.current['keyboardBaselineUptime']=time.monotonic()
                result.update(actionIndex=self.current['actionIndex'],keyboardPhase='acquire' if not cursor.acquired else 'disabled-probe' if cursor.spec['mode']=='disabled' and cursor.phase_index==0 and not cursor.held_space else cursor.phases[cursor.phase_index])
                return result
            if op=='evaluate' and type(body) is dict and set(body)=={'keyboardWitness'}:
                o.require('baseline' in self.current,'Keyboard baseline required')
                binding={'case':self.current['case'],'generation':self.generation,'actionIndex':self.current['actionIndex'],
                         'baselineUptime':self.current['keyboardBaselineUptime'],'evaluatedUptime':time.monotonic()}
                w=o.witness(body['keyboardWitness'],binding);cursor.check(w)
                self.save('keyboard-witness-'+str(self.current['actionIndex']),{'binding':binding,'witness':w})
                # The raw app capture remains immutable. Annotate only the in-memory
                # baseline used for the strict verdict; the witness has its own file.
                baseline=copy.deepcopy(self.current['baseline']);baseline.update(keyboardWitness=w,keyboardBinding=binding)
                self.current['baseline']=baseline
                result=super()._request(op,{})
                if result['passed'] is True:cursor.advance(w)
                else:cursor.failed=True
                return result
            if op=='evaluate':
                # Ordinary parent evaluation stays unchanged, but keyboard verdicts
                # reject the absent witness and cannot advance their closed cursor.
                result=super()._request(op,body);cursor.failed=True;return result
            return super()._request(op,body)
    return KeyboardBridge
