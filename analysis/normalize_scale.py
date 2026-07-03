#!/usr/bin/env python3
"""One-shot normalizer: replace literal font-size (rem) and spacing (margin/
padding/gap) values with the design-system --text-*/--space-* tokens, snapping
each to its nearest ramp step. Operates only inside CSS contexts (style.css, a
page's <style> block, and inline style="" / style='' attributes) — never
touches arbitrary JS. Negatives and bare `0` are left literal; positive rem
values floor at --space-1 so small paddings don't collapse to zero.

Idempotent-ish: re-running is a no-op because literals are already gone.
"""
import re, glob, os

ROOT = os.path.join(os.path.dirname(__file__), '..', 'site')

# ramp step (rem) -> token name  (must match :root in style.css)
TYPE = {.72:'--text-xs', .82:'--text-sm', .9:'--text-base', 1.0:'--text-md',
        1.15:'--text-lg', 1.25:'--text-xl', 1.5:'--text-2xl', 1.7:'--text-3xl', 2.7:'--text-hero'}
SPACE = {.25:'--space-1', .5:'--space-2', .75:'--space-3', 1.0:'--space-4', 1.25:'--space-5',
         1.5:'--space-6', 2.0:'--space-8', 2.5:'--space-10', 3.0:'--space-12', 4.0:'--space-16', 5.0:'--space-20'}
SPACE_PROPS = ['margin-top','margin-bottom','margin-left','margin-right','margin',
               'padding-top','padding-bottom','padding-left','padding-right','padding','gap']

def nearest(v, table):
    step = min(table, key=lambda s: abs(s - v))
    return table[step]

stats = {'font-size':0, 'spacing':0}

def type_sub(text):
    def r(m):
        stats['font-size'] += 1
        return f"font-size:var({nearest(float(m.group(1)), TYPE)})"
    return re.sub(r'font-size\s*:\s*([0-9]*\.?[0-9]+)rem', r, text)

# a positive rem literal NOT preceded by '-' or a word char/dot (so -.3rem and 1.5rem-in-a-word are skipped)
REM = re.compile(r'(?<![-\w.])([0-9]*\.?[0-9]+)rem')

def space_sub(text):
    for prop in SPACE_PROPS:
        def r(m):
            head, val = m.group(1), m.group(2)
            def tok(t):
                stats['spacing'] += 1
                return f"var({nearest(float(t.group(1)), SPACE)})"
            return head + REM.sub(tok, val)
        text = re.sub(rf'(\b{prop}\s*:\s*)([^;}}\n]+)', r, text)
    return text

def css_transform(text):
    return space_sub(type_sub(text))

def process_file(path):
    src = open(path).read()
    before = dict(stats)
    if path.endswith('.css'):
        out = css_transform(src)
    else:  # html: only <style> blocks and inline style attributes
        out = re.sub(r'(<style[^>]*>)(.*?)(</style>)',
                     lambda m: m.group(1) + css_transform(m.group(2)) + m.group(3), src, flags=re.S)
        out = re.sub(r'(style\s*=\s*)"([^"]*)"', lambda m: m.group(1) + '"' + css_transform(m.group(2)) + '"', out)
        out = re.sub(r"(style\s*=\s*)'([^']*)'", lambda m: m.group(1) + "'" + css_transform(m.group(2)) + "'", out)
    if out != src:
        open(path, 'w').write(out)
    d = {k: stats[k] - before[k] for k in stats}
    if d['font-size'] or d['spacing']:
        print(f"  {os.path.basename(path):22} font-size:{d['font-size']:3}  spacing:{d['spacing']:3}")

print("Normalizing to --text-*/--space-* tokens:")
process_file(os.path.join(ROOT, 'assets', 'style.css'))
for f in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
    process_file(f)
print(f"\nTOTAL: {stats['font-size']} font-size + {stats['spacing']} spacing literals tokenized.")
