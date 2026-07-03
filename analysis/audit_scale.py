#!/usr/bin/env python3
"""Scale audit + guard for the design system.

Reports how font-size, font-weight, line-height, and spacing (margin/padding/gap)
are expressed across every CSS context in site/ (the stylesheet, each page's
<style> block, and inline style="" / style='' attributes), and FAILS (exit 1)
if any *literal rem* font-size or spacing value has crept back in instead of a
--text-*/--space-* token.

Exempt on purpose (not violations):
  - px values: SVG chart coordinate space, the 15px body base, tiny chart gaps
  - negative margins (can't be a positive token; handful, left literal)
  - em/ch/% and the :root token definitions themselves

Run:  python3 analysis/audit_scale.py          # report + pass/fail
Used by tests/test_scale_tokens.py as a regression gate.
"""
import re, glob, os, sys, collections

ROOT = os.path.join(os.path.dirname(__file__), '..', 'site')
SPACE_PROPS = ['margin-top','margin-bottom','margin-left','margin-right','margin',
               'padding-top','padding-bottom','padding-left','padding-right','padding','gap']
# a POSITIVE rem literal (negatives excluded so -.3rem is exempt)
POS_REM = re.compile(r'(?<![-\w.])[0-9]*\.?[0-9]+rem')

def css_contexts():
    """(label, css_text) for the stylesheet, every <style> block, every inline style."""
    yield ('assets/style.css', open(os.path.join(ROOT, 'assets/style.css')).read())
    for path in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
        f = os.path.basename(path)
        t = open(path).read()
        for m in re.finditer(r'<style[^>]*>(.*?)</style>', t, re.S):
            yield (f + ' <style>', m.group(1))
        for m in re.finditer(r'style\s*=\s*["\']([^"\']*)["\']', t):
            yield (f + ' inline', m.group(1))

def audit():
    ctx = list(css_contexts())
    blob = '\n'.join(c for _, c in ctx)

    def counter(pattern):
        c = collections.Counter()
        for m in re.finditer(pattern, blob):
            c[m.group(1).strip()] += 1
        return c

    report = {
        'font-size':   counter(r'font-size\s*:\s*([^;}\n]+)'),
        'font-weight': counter(r'font-weight\s*:\s*([^;}\n]+)'),
        'line-height': counter(r'line-height\s*:\s*([^;}\n]+)'),
    }
    # spacing: collect the raw length tokens used
    spacing = collections.Counter()
    for prop in SPACE_PROPS:
        for m in re.finditer(rf'\b{prop}\s*:\s*([^;}}\n]+)', blob):
            for tok in re.findall(r'-?[0-9]*\.?[0-9]+(?:rem|px|em)', m.group(1)):
                spacing[tok] += 1

    # ---- violations: positive rem literals in font-size or spacing ----
    violations = []
    for label, css in ctx:
        for m in re.finditer(r'font-size\s*:\s*([0-9]*\.?[0-9]+rem)', css):
            violations.append((label, 'font-size', m.group(1)))
        for prop in SPACE_PROPS:
            for m in re.finditer(rf'\b{prop}\s*:\s*([^;}}\n]+)', css):
                for tok in POS_REM.findall(m.group(1)):
                    violations.append((label, prop, tok))
    return report, spacing, violations

def main():
    report, spacing, violations = audit()
    for prop, c in report.items():
        lit = {k: v for k, v in c.items() if 'var(' not in k}
        tok = sum(v for k, v in c.items() if 'var(' in k)
        print(f"\n{prop}: {tok} token uses · {len(lit)} literal value(s) "
              + (f"→ {dict(sorted(lit.items(), key=lambda x:-x[1]))}" if lit else ""))
    lit_sp = {k: v for k, v in spacing.items() if not k.endswith(('rem',)) or k.startswith('-')}
    print(f"\nspacing: {sum(v for k,v in spacing.items() if k.endswith('rem') and not k.startswith('-'))} "
          f"rem-token-adjacent · exempt literals (px/neg): {dict(lit_sp)}")

    if violations:
        print(f"\n❌ {len(violations)} off-token literal(s) — use --text-*/--space-*:")
        for label, prop, tok in violations[:40]:
            print(f"   {label:24} {prop}: {tok}")
        sys.exit(1)
    print("\n✅ No literal rem font-size/spacing outside the token ramps.")

if __name__ == '__main__':
    main()
