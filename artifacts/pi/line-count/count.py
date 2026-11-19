import collections
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[3] / 'repos/pi'
files = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
counts = collections.defaultdict(lambda: [0, 0, 0])
excluded_generated = [0, 0]
for path in files:
    parts = path.split('/')
    if len(parts) < 4 or parts[0] not in ('packages', 'apps') or parts[2] != 'src' or parts[1] == 'evals':
        continue
    if set(parts) & {'test', 'tests', '__tests__', 'fixtures', '__fixtures__', 'examples', 'generated'}:
        continue
    if not path.endswith(('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.css', '.rs', '.c', '.h', '.cc', '.cpp')) or path.endswith('.d.ts') or '.test.' in path or '.spec.' in path:
        continue
    lines = (root / path).read_text(errors='replace').splitlines()
    if any('auto-generated' in line.lower() or 'automatically generated' in line.lower() for line in lines[:3]):
        excluded_generated[0] += 1
        excluded_generated[1] += len(lines)
        continue
    row = counts['/'.join(parts[:2])]
    row[0] += len(lines)
    row[1] += sum(bool(line.strip()) for line in lines)
    row[2] += 1
for name, row in sorted(counts.items()):
    print(name, *row)
print('TOTAL', *(sum(row[i] for row in counts.values()) for i in range(3)))
print('EXCLUDED_GENERATED_FILES_LINES', *excluded_generated)
