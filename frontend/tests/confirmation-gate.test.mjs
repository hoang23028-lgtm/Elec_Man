import assert from 'node:assert/strict';
import test from 'node:test';
import { ConfirmationGate } from '../lib/confirmation-gate.ts';

test('no action is accepted before an explicit decision', async () => {
  const gate = new ConfirmationGate();
  const decision = gate.begin();
  let settled = false;
  decision.then(() => { settled = true; });
  await Promise.resolve();
  assert.equal(settled, false);
  gate.finish(true);
  assert.equal(await decision, true);
});

test('cancelling or unmounting resolves false, not approval', async () => {
  const gate = new ConfirmationGate();
  const decision = gate.begin();
  gate.finish(false);
  assert.equal(await decision, false);
});

test('duplicate requests cannot replace the pending decision', async () => {
  const gate = new ConfirmationGate();
  const first = gate.begin();
  assert.equal(gate.begin(), null);
  gate.finish(false);
  assert.equal(await first, false);
  const next = gate.begin();
  gate.finish(true);
  assert.equal(await next, true);
});

test('duplicate completion is harmless and cannot affect the next prompt', async () => {
  const gate = new ConfirmationGate();
  const first = gate.begin();
  gate.finish(false);
  gate.finish(true);
  assert.equal(await first, false);
  const next = gate.begin();
  gate.finish(false);
  assert.equal(await next, false);
});
