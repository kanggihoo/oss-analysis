# out/*.html 에서 SVG 루트 viewBox와 경로 점(data-composition-points)·노드 id를 뽑는다.
import re, glob
for f in sorted(glob.glob('out/*.html')):
    s = open(f).read()
    vb = re.search(r'<svg viewBox="([^"]*)"', s)
    print('==', f, vb.group(1) if vb else None)
    for m in re.finditer(r'<path[^>]*?data-edge-from="([^"]*)"[^>]*?data-edge-to="([^"]*)"[^>]*?data-composition-points="([^"]*)"', s):
        print('  edge', m.group(1), '->', m.group(2), m.group(3))
    for m in re.finditer(r'<path[^>]*data-er-trunk[^>]*data-composition-points="([^"]*)"', s):
        print('  trunk', m.group(1))
