# Verification

Run from the project root with Python 3.11+:

```console
python -B -m unittest discover -s tests -v
```

Actual local result on 2026-11-03: **26 tests, 25 passed, 1 skipped** under
CPython 3.11.15 on Windows 10 build 26300. The symlink test was skipped because
this Windows session could not create a symlink. No Linux/macOS result is
claimed. Tests run the CLI by basename from the repository root, including
real subprocesses whose stdout reader is closed before completion.

Behavior coverage: exact replacement; mismatching context at a fixed position;
matching text elsewhere does not rescue a mismatch; beginning/middle/end and
empty-base insertion; deletion; cumulative multi-hunk delta; CRLF normalization;
empty logical lines; malformed counts, overlap, old ordering, wrong new offsets,
huge numbers, and out-of-base coordinates; unsupported metadata, multiple files,
combined/binary/rename forms and no-newline markers; encoding; byte/line/hunk
limits including inclusive accepted boundaries; path privacy and unsupported
path forms; input hashes and modification timestamps remain unchanged; help,
usage, and closed stdout preserve exit status without stderr or exit 120.

The parent batch's `builder-evidence/patch-context-check/red.log` records the
initial 22-test run before production code existed: 53 assertion failures and
one symlink skip. The missing CLI was the expected absent behavior, not an
import/discovery error. `green.log` records the completed suite. Two further
tests strengthen inclusive-boundary and opaque-header verification after the
initial green run; they did not require a production change.
`red-device.log` records a subsequent failing test for lexical rejection of
console-device names; the fix is included in the final green run.

Controller integration found that plain text reports did not satisfy the batch's
JSON handoff contract. `red-json.log` preserves three actual JSON decoding errors
before the repair; `green-json.log` records 26 tests with one environmental skip
after clean, mismatch and invalid reports became deterministic JSON. Help remains
fixed text. The parent preserved the pre-repair controller result separately.

`checks.json` contains five independently runnable committed fixture commands
with expected exit codes. For a portable automated check from this directory:

```python
import json
import subprocess
import sys

with open("checks.json", encoding="utf-8") as stream:
    checks = json.load(stream)
for check in checks:
    result = subprocess.run([sys.executable, "-B", *check["args"]])
    assert result.returncode == check["exit"]
```

Actual fixture result: 5/5 expected exit codes, covering clean 0, mismatch 1,
unsupported 2, insertion 0, and help 0. No test executes Git, applies a patch,
or changes an input. Temporary files are created by the tests, not by the CLI.
