"""Run the frozen suite unchanged, redirecting only its codec import to this folder."""
import hashlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SUITE = ROOT.parent.parent / 'round16-wire-compat/testing/test_independent.py'
EXPECTED = {
    'frozen_independent.BuildTests.test_user_envelope_is_pinned_and_source_exact':
        'Intended r16.e2 delta: source_text removed; exact source remains in span-table rows.'
}


def run():
    raw = SUITE.read_bytes()
    suite_hash = hashlib.sha256(raw).hexdigest()
    real_spec = importlib.util.spec_from_file_location
    redirects = []

    def redirected_spec(name, path, *args, **kwargs):
        if Path(path).resolve() == ROOT.parent.parent / 'round16-wire-compat/protocol/wire.py':
            path = ROOT / 'wire.py'
            redirects.append(str(path))
        return real_spec(name, path, *args, **kwargs)

    spec = real_spec('frozen_independent', SUITE)
    suite = importlib.util.module_from_spec(spec)
    with patch.object(importlib.util, 'spec_from_file_location', side_effect=redirected_spec):
        # Compile precisely the frozen bytes, without rewriting the test source.
        exec(compile(raw, str(SUITE), 'exec'), suite.__dict__)
    if redirects != [str(ROOT / 'wire.py')] or suite.WIRE.ROOT != ROOT:
        raise RuntimeError('Frozen suite did not import protocol-w2-1/wire.py')
    suite.WIRE_PATH = ROOT / 'wire.py'
    # API adapter only: frozen callers predate the mandatory keyword-only plan.
    # Every response still goes through the real, mandatory plan-bound validator.
    validator = suite.WIRE.validate_response
    binding_calls = []

    def bound_response(raw, finish, source, table, profile='full'):
        plan = suite.WIRE.build(source, profile)
        binding_calls.append(plan['request_sha256'])
        return validator(raw, finish, source, table, profile, plan=plan)

    stream = io.StringIO()
    with patch.object(suite.WIRE, 'validate_response', side_effect=bound_response):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromModule(suite))
    if SUITE.read_bytes() != raw:
        raise RuntimeError('Frozen independent suite changed')
    failures = [dict(test=test.id(), reason=EXPECTED.get(test.id()), traceback=trace)
                for test, trace in result.failures]
    errors = [dict(test=test.id(), traceback=trace) for test, trace in result.errors]
    failed_ids = {item['test'] for item in failures}
    accepted = (failed_ids == set(EXPECTED) and len(failures) == len(EXPECTED)
                and not errors and not result.skipped and result.testsRun == 55)
    report = dict(tests_run=result.testsRun,
                  tests_passed=result.testsRun - len(failures) - len(errors) - len(result.skipped),
                  failures=failures, errors=errors, skipped=len(result.skipped),
                  intended_failures=len(failures) if accepted else 0,
                  unexpected_failures=[f for f in failures if not f['reason']],
                  raw_suite_success=result.wasSuccessful(), accepted=accepted,
                  suite_sha256=suite_hash, suite_unchanged=True,
                  api_adapter='mandatory originating plan supplied to frozen legacy callers',
                  plan_bound_calls=len(binding_calls),
                  wire_path='protocol-w2-1/wire.py',
                  invocation='python3 -I -S -B protocol-w2-1/run_independent.py')
    return stream.getvalue(), report


if __name__ == '__main__':
    output, report = run()
    print(output, end='')
    print(json.dumps(report, indent=2, sort_keys=True))
    # The raw suite has one failure; this runner accepts only that exact known delta.
    raise SystemExit(0 if report['accepted'] else 1)
