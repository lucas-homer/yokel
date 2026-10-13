#!/usr/bin/env python3
"""Compile only nonsecret reviewed policy into a native runner, on the Mac Mini."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--policy', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--synthetic-tests', action='store_true', help='Compile test-only hooks; never enroll a test build.')
args = parser.parse_args()
policy = args.policy.read_bytes()
# Avoid printing policy contents, even if the wrong file was supplied.
try:
    parsed = json.loads(policy)
    if set(parsed) != {'schema_version', 'base_policy', 'public_key_base64', 'registry_dir', 'journal_dir', 'python_path', 'adapter_roots', 'dependency_roots', 'timeout_max_seconds'}:
        raise ValueError()
    if parsed['schema_version'] != 'yokel.stable-core.v1' or parsed['base_policy'].get('jobs') != {}:
        raise ValueError()
except (ValueError, TypeError):
    parser.error('Invalid nonsecret policy schema; do not supply credential files.')
output = args.output.absolute()
if output.exists() or output.is_symlink():
    parser.error('Output already exists; build to a new path and review before replacing an enrolled binary.')
output.parent.mkdir(parents=True, exist_ok=True)
source = Path(__file__).resolve().parent
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix='yokel-research-build-') as temporary:
    folder = Path(temporary)
    embedded = folder / 'EmbeddedPolicy.h'
    encoded = base64.b64encode(policy).decode('ascii')
    embedded.write_text('static NSString *const EmbeddedPolicy = @"' + encoded + '";\n')
    flags = ['-DYOKEL_SYNTHETIC_TESTS'] if args.synthetic_tests else []
    subprocess.run(['/usr/bin/xcrun', 'clang', '-fobjc-arc', '-fblocks', '-O2',
                    '-Wall', '-Wextra', '-Wno-deprecated-declarations',
                    '-framework', 'Foundation', '-framework', 'Security',
                    '-I', str(folder), *flags, str(source / 'runner.m'),
                    '-o', str(output)], check=True)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime,restrict,kill', str(output)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(output)], check=True)
    signature = subprocess.run(['/usr/bin/codesign', '--display', '--verbose=4', str(output)],
                               capture_output=True, text=True, check=True)
    if 'runtime' not in signature.stderr or 'restrict' not in signature.stderr or 'kill' not in signature.stderr:
        raise RuntimeError('Required hardened-runtime code-signing flags missing')
    subprocess.run([str(output), 'check-policy'], check=True)
os.chmod(output, 0o700)
print('Stable candidate built; no enrollment or credential access performed.')
