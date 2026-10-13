"""Round-3 review repro: what does the run_independent.py adapter change per frozen test?

Runs the frozen testing/test_independent.py three ways and records, per test, the
outcome of every validate_response call (ACCEPT or exception type:code):
  (a) protocol-w2/wire.py, native call (w2's optional plan, no adapter)
  (b) protocol-w2-1/wire.py, with the w2.1 adapter (plan=build(source, profile))
  (c) protocol-w2-1/wire.py, native call, no adapter
"""
import collections
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
SUITE = ROUND / 'testing/test_independent.py'
RAW = SUITE.read_bytes()


def code_of(exc):
    code = getattr(exc, 'code', None)
    return type(exc).__name__ + ':' + (code if isinstance(code, str) else str(exc)[:50])


def run(wire_path, adapter):
    real_spec = importlib.util.spec_from_file_location

    def redirected(name, path, *args, **kwargs):
        if Path(path).resolve() == ROUND / 'protocol/wire.py':
            path = wire_path
        return real_spec(name, path, *args, **kwargs)

    spec = real_spec('frozen_independent', SUITE)
    suite = importlib.util.module_from_spec(spec)
    with patch.object(importlib.util, 'spec_from_file_location', side_effect=redirected):
        exec(compile(RAW, str(SUITE), 'exec'), suite.__dict__)
    assert suite.WIRE.ROOT == wire_path.parent, suite.WIRE.ROOT
    records = collections.defaultdict(list)
    current = ['<none>']
    validator = suite.WIRE.validate_response

    def wrapped(raw, finish, source, table, profile='full', **kw):
        try:
            if adapter:
                try:
                    plan = suite.WIRE.build(source, profile)
                except Exception as exc:
                    records[current[0]].append('build!' + code_of(exc))
                    raise
                out = validator(raw, finish, source, table, profile, plan=plan)
            else:
                out = validator(raw, finish, source, table, profile, **kw)
        except Exception as exc:
            records[current[0]].append(code_of(exc))
            raise
        records[current[0]].append('ACCEPT')
        return out

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            current[0] = test.id().split('.', 1)[1]
            super().startTest(test)

    suite.WIRE.validate_response = wrapped
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0, resultclass=Result).run(
        unittest.defaultTestLoader.loadTestsFromModule(suite))
    summary = dict(run=result.testsRun, failures=[t.id().split('.', 1)[1] for t, _ in result.failures],
                   errors=[t.id().split('.', 1)[1] for t, _ in result.errors], skipped=len(result.skipped))
    return summary, dict(records)


a_sum, a = run(ROUND / 'protocol-w2/wire.py', adapter=False)
b_sum, b = run(ROUND / 'protocol-w2-1/wire.py', adapter=True)
c_sum, c = run(ROUND / 'protocol-w2-1/wire.py', adapter=False)
print('(a) w2 native      :', a_sum)
print('(b) w2.1 + adapter :', b_sum)
print('(c) w2.1 native    :', c_sum, '<- errors are the frozen callers that omit plan')
print()
print('validate_response calls: (a) %d  (b) %d  (c) %d' % (sum(map(len, a.values())), sum(map(len, b.values())), sum(map(len, c.values()))))
print()
tests = sorted(set(a) | set(b))
print('Tests calling validate_response (adapter-affected):', len(tests))
changed = []
for test in tests:
    ca, cb = collections.Counter(a.get(test, [])), collections.Counter(b.get(test, []))
    if ca != cb:
        changed.append(test)
        print('\nDIFFERENT PATH:', test)
        print('   (a) w2 native     :', dict(ca))
        print('   (b) w2.1 adapter  :', dict(cb))
print('\nTests whose per-call outcomes are identical under (a) and (b):', len(tests) - len(changed))
for test in tests:
    if test not in changed:
        print('   same:', test, dict(collections.Counter(b[test])))
print('\nAny call that was a rejection under (a) but ACCEPT under (b)?')
flips = [(t, i, x, y) for t in tests for i, (x, y) in enumerate(zip(a.get(t, []), b.get(t, []))) if x != 'ACCEPT' and y == 'ACCEPT']
print('   ', flips or 'none')
print('Any ACCEPT under (a) that is a rejection under (b)?')
flips = [(t, i, x, y) for t in tests for i, (x, y) in enumerate(zip(a.get(t, []), b.get(t, []))) if x == 'ACCEPT' and y != 'ACCEPT']
print('   ', flips or 'none')
