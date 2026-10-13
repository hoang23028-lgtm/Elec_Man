import assert from 'node:assert/strict';
import test from 'node:test';
import { canAccessPage, canOperate } from '../types/auth.ts';

test('viewer and guest only see dashboard, including direct hash navigation', () => {
  for (const role of [null, 'VIEWER']) {
    assert.equal(canAccessPage(role, 'dashboard'), true);
    for (const page of ['operations', 'batches', 'administration', 'model-lifecycle', 'traceability']) {
      assert.equal(canAccessPage(role, page), false);
    }
  }
});
test('operations admin cannot enter system administration or training', () => {
  for (const page of ['operations', 'batches', 'administration']) {
    assert.equal(canAccessPage('ADMIN', page), true);
  }
  for (const page of ['model-lifecycle', 'traceability']) {
    assert.equal(canAccessPage('ADMIN', page), false);
    assert.equal(canAccessPage('SUPER_ADMIN', page), true);
  }
  assert.equal(canOperate('SUPER_ADMIN'), true);
  assert.equal(canAccessPage('SUPER_ADMIN', 'unknown'), false);
});
