"""Deterministic tests of actual cache runner logic; no inner OS children/groups."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
import adopt_fixture as adoption

HERE = Path(__file__).resolve().parent
MODE = 'optimized' if sys.flags.optimize else 'normal'
EVIDENCE = HERE / ('fake-' + MODE)
EVIDENCE.mkdir()


def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn',
                 'os.kill', 'os.killpg', 'os.exec', 'os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('No inner process/group/socket operation: ' + event)
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            if not Path(os.fsdecode(args[0])).resolve().is_relative_to(HERE):
                raise RuntimeError('Write outside owned directory')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'}:
        for p in args[:2] if event == 'os.rename' else args[:1]:
            if not Path(os.fsdecode(p)).resolve().is_relative_to(HERE):
                raise RuntimeError('Mutation outside owned directory')


sys.addaudithook(audit)
sys.dont_write_bytecode = True


def namespace(module, **changes):
    values = vars(module).copy()
    values.update(changes)
    return types.SimpleNamespace(**values)


class World:
    def __init__(self, kind):
        self.kind, self.events, self.clock = kind, [], 0.0
        self.reaped = False
        self.live = kind in {'timeout-denial', 'timeout-success'}
        self.descendant = kind == 'surviving-descendant'
        self.denied = False
        self.returncode = None if self.live else 0
        self.pid = 987654321
        self.stdout, self.stderr = self.Pipe(101), self.Pipe(102)
        self.keys = {}
        self.reads = 0

    class Pipe:
        def __init__(self, fd): self.fd = fd
        def fileno(self): return self.fd
        def close(self): pass

    def monotonic(self):
        self.clock += .02
        return self.clock

    def sleep(self, seconds): self.clock += seconds

    def poll(self):
        self.events.append('poll')
        if not self.live:
            self.reaped = True
            return self.returncode
        return None

    def wait(self, timeout):
        self.events.append('wait')
        if self.live:
            raise RuntimeError('Fake wait while still live')
        self.reaped = True
        return self.returncode

    def group(self, pid, sig):
        if pid != self.pid:
            raise RuntimeError('Unexpected fake group identity')
        self.events.append('group:' + str(sig))
        if self.kind == 'permission' or (self.kind == 'leader-zombie' and not self.reaped) or (
                self.kind == 'timeout-denial' and self.reaped):
            self.denied = True
            self.events.append('EPERM')
            raise PermissionError(1, 'synthetic permission/ineligible-member denial')
        if not self.live and not self.descendant:
            raise ProcessLookupError(3, 'synthetic positive absence')
        if sig:
            self.live = self.descendant = False
            self.returncode = -9

    def register(self, pipe, event, data):
        self.keys[pipe] = types.SimpleNamespace(fileobj=pipe, data=data)

    def select(self, seconds):
        self.clock += seconds
        return [(key, None) for key in list(self.keys.values())]

    def read(self, fd, count):
        self.reads += 1
        if self.kind == 'read-error':
            raise OSError(5, 'synthetic read failure before EOF')
        if self.live:
            return b'waiting\n'
        return b''

    def selector(self):
        return types.SimpleNamespace(register=self.register, get_map=lambda: self.keys,
            select=self.select, unregister=lambda pipe: self.keys.pop(pipe), close=lambda: None)


class Controls(unittest.TestCase):
    def runner(self, candidate=True):
        runner = adoption.previous().previous().load_runner(EVIDENCE / 'unused')
        return adoption.install(runner) if candidate else runner

    def context(self, name, world, candidate=True):
        runner = self.runner(candidate)
        destination = EVIDENCE / name
        destination.mkdir()
        runner.os = namespace(runner.os, killpg=world.group, read=world.read)
        runner.time = types.SimpleNamespace(monotonic=world.monotonic, sleep=world.sleep)
        runner.selectors = namespace(runner.selectors, DefaultSelector=world.selector)
        def spawn(*a, **kw):
            world.events.append('spawn')
            return world
        runner.subprocess = namespace(runner.subprocess, Popen=spawn)
        runner.CHILD_SECONDS = .15
        runner.child_usage = lambda: dict(ru_utime=0., ru_stime=0., ru_minflt=0, ru_majflt=0)
        commands = runner.Commands(destination, {'commands': []}, 20)
        scratch = destination / 'scratch'
        scratch.mkdir()
        commands.bind_scratch(scratch)
        return runner, commands

    def retain(self, name, world, commands):
        (EVIDENCE / (name + '.json')).write_text(json.dumps({
            'events': world.events, 'reaped': world.reaped, 'denied': world.denied,
            'scratch_preserved': commands.scratch.exists(), 'receipt': commands.receipt,
            'synthetic_group_only': True}, indent=2) + '\n')

    def test_unreaped_leader_discriminates_order(self):
        for candidate in [False, True]:
            world = World('leader-zombie')
            name = 'leader-' + str(candidate)
            runner, commands = self.context(name, world, candidate)
            row = {'child_returned': False, 'owned_group_gone': False}
            if candidate:
                commands.stop(world, row)
                self.assertTrue(row['child_returned'] and row['owned_group_gone'])
                self.assertEqual(world.events[0], 'poll')
            else:
                with self.assertRaises(PermissionError): commands.stop(world, row)
                self.assertEqual(world.events[0], 'group:0')
                self.assertFalse(world.reaped)
            commands.receipt['direct_stop'] = row
            self.retain(name, world, commands)

    def test_live_descendant_survives_leader_reap(self):
        world = World('surviving-descendant')
        runner, commands = self.context('descendant', world)
        row = {'child_returned': False, 'owned_group_gone': False}
        commands.stop(world, row)
        self.assertIn('group:9', world.events)
        self.assertTrue(row['owned_group_gone'])
        self.assertTrue(world.reaped)
        self.retain('descendant', world, commands)

    def test_actual_permission_denial_stays_unknown(self):
        world = World('permission')
        runner, commands = self.context('permission', world)
        row = {'child_returned': False, 'owned_group_gone': False}
        with self.assertRaises(PermissionError): commands.stop(world, row)
        before = list(world.events)
        for fn in [lambda: commands.stop(world, row), lambda: commands.gone(world.pid),
                   lambda: commands.run('forbidden', ['fake'], commands.out)]:
            with self.assertRaises(RuntimeError): fn()
        self.assertEqual(world.events, before)
        self.assertFalse(row['owned_group_gone'])
        self.retain('permission', world, commands)

    def test_inherited_timeout_post_reap_denial_and_finalizer(self):
        for candidate in [False, True]:
            world = World('timeout-denial')
            name = 'post-reap-' + str(candidate)
            runner, commands = self.context(name, world, candidate)
            with self.assertRaises(PermissionError):
                commands.run('descendant', ['fake'], commands.out)
            row = commands.receipt['commands'][-1]
            self.retain(name, world, commands)
            self.assertTrue(row['child_returned'])
            self.assertTrue(row['owned_group_killed'])
            self.assertTrue(row['timed_out'])
            self.assertFalse(row['owned_group_gone'])
            self.assertTrue(row['custody_hold'])
            self.assertIsNone(row['child_resource_usage']['aggregate_delta'])
            denial = world.events.index('EPERM')
            if candidate:
                self.assertEqual(world.events[denial + 1:], [])
                self.assertEqual(len(row['errors']), 1)
                before = list(world.events)
                with self.assertRaises(RuntimeError): commands.run('forbidden', ['fake'], commands.out)
                self.assertEqual(world.events, before)
            else:
                self.assertEqual([e['phase'] for e in row['errors']], ['active', 'stop-owned-group'])
                self.assertIn('group:0', world.events[denial + 1:])

    def test_positive_absence_and_both_eofs_release(self):
        world = World('success')
        runner, commands = self.context('success', world)
        _, _, row = commands.run('success', ['fake'], commands.out)
        self.assertTrue(all(row[k] for k in ['child_returned', 'owned_group_gone', 'stdout_eof', 'stderr_eof']))
        self.assertFalse(row['custody_hold'])
        self.assertIsNone(commands.active)
        self.assertIsNotNone(row['child_resource_usage']['aggregate_delta'])
        self.retain('success', world, commands)

    def test_forced_close_does_not_claim_eof(self):
        world = World('read-error')
        runner, commands = self.context('no-eof', world)
        with self.assertRaises(OSError): commands.run('failure', ['fake'], commands.out)
        row = commands.receipt['commands'][-1]
        self.assertTrue(row['child_returned'] and row['owned_group_gone'])
        self.assertFalse(row['stdout_eof'] or row['stderr_eof'])
        self.assertTrue(row['custody_hold'])
        self.assertIsNone(row['child_resource_usage']['aggregate_delta'])
        self.retain('no-eof', world, commands)

    def test_successful_timeout_cleanup_still_fails_command(self):
        world = World('timeout-success')
        runner, commands = self.context('timeout-success', world)
        with self.assertRaises(RuntimeError): commands.run('timeout', ['fake'], commands.out)
        row = commands.receipt['commands'][-1]
        self.assertTrue(row['timed_out'] and row['owned_group_gone'])
        self.assertFalse(row['custody_hold'])
        self.retain('timeout-success', world, commands)

    def test_seals_and_frozen_fixture(self):
        proof = adoption.verify()
        self.assertFalse(proof['compiler_qualified'])
        original = adoption.SOURCE.read_text()
        derivative = original.replace((HERE / 'original-commands.py').read_text(), (HERE / 'commands.py').read_text(), 1)
        before = ast.parse(original)
        after = ast.parse(derivative)
        def outside(tree):
            return [ast.dump(n, include_attributes=False) for n in tree.body
                    if not isinstance(n, ast.ClassDef) or n.name != 'Commands']
        self.assertEqual(outside(before), outside(after))
        original_controls = (adoption.OLD / 'runner-controls.py').read_text()
        owner = next(n for n in ast.parse(original_controls).body if isinstance(n, ast.ClassDef) and n.name == 'RunnerControls')
        self.assertEqual(len([n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]), 36)
        self.assertEqual(adoption.previous().previous().COMPILER_SHA256,
            '1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1')
        with mock.patch.object(adoption, 'WORKFLOW', HERE / 'workflow-job.yml'):
            self.assertTrue(adoption.verify(True)['installed'])
        with self.assertRaisesRegex(RuntimeError, 'Installed job differs'):
            adoption.verify(True)

    def test_prospective_wrapper_reuses_compiler_and_fixture(self):
        old = adoption.previous()
        compiler = old.previous()
        seen = []
        def pretend(output, rustc):
            runner = compiler.load_runner(output)
            self.assertEqual(Path(runner.Commands.run.__code__.co_filename), HERE / 'commands.py')
            self.assertEqual(Path(runner.verify_methods.__code__.co_filename), adoption.SOURCE)
            self.assertEqual((runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.CHILD_SECONDS, runner.OUTPUT_CAP),
                (600, 60, 60, 8388608))
            seen.append(compiler.verify(True))
            return 17
        compiler.run_fixture = pretend
        real_previous = adoption.previous
        calls = []
        def selected_previous():
            module = real_previous()
            calls.append(1)
            if len(calls) == 2:
                module.previous = lambda: compiler
            return module
        with mock.patch.object(adoption, 'previous', side_effect=selected_previous), \
             mock.patch.object(adoption, 'WORKFLOW', HERE / 'workflow-job.yml'):
            self.assertEqual(adoption.run_fixture(EVIDENCE / 'never-created', 'never-executed'), 17)
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0]['installed_job_verified'])

    def test_derivative_mutation_refused(self):
        real = adoption.previous
        def previous():
            old = real()
            previous_compiler = old.previous
            def compiler():
                c = previous_compiler()
                baseline = c.baseline
                def altered():
                    b = baseline()
                    original = b.sha
                    b.sha = lambda p: '0' * 64 if p == HERE / 'commands.py' else original(p)
                    return b
                c.baseline = altered
                return c
            old.previous = compiler
            return old
        with mock.patch.object(adoption, 'previous', side_effect=previous):
            with self.assertRaises(RuntimeError): adoption.verify()


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    (EVIDENCE / 'result.json').write_text(json.dumps({'tests': result.testsRun,
        'failures': [(str(c), e) for c, e in result.failures],
        'errors': [(str(c), e) for c, e in result.errors], 'successful': result.wasSuccessful(),
        'python': sys.version, 'mode': MODE, 'scope': 'Deterministic fake OS only; no native or compiler qualification'}, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() else 1)
