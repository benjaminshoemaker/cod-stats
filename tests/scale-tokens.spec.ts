import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

// Design-system guard: the type/spacing scale must stay tokenized. The Python
// audit (analysis/audit_scale.py) scans style.css, every <style> block, and
// inline style="" across site/, and exits non-zero (listing offenders) if any
// literal rem font-size or spacing value has crept back instead of a
// --text-*/--space-* token. Runs once, independent of the browser projects.
test('design system: type & spacing stay on the token ramps', () => {
  test.skip(test.info().project.name !== 'desktop', 'run once');
  try {
    execFileSync('python3', ['analysis/audit_scale.py'], { stdio: 'pipe' });
  } catch (e: any) {
    throw new Error('Scale audit failed — off-ramp literals reintroduced:\n' +
      (e.stdout?.toString() || e.stderr?.toString() || e.message));
  }
});
