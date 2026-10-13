import assert from 'node:assert/strict';
import test from 'node:test';
import { readingLabelStatus } from '../lib/review-status.ts';

test('an AI value stored by the worker is not a human-verified label', () => {
  assert.equal(readingLabelStatus('PENDING', '00120', '00120'), 'AI đề xuất · chưa lưu nhãn');
  assert.equal(readingLabelStatus(null, '00120', '00120'), 'AI đề xuất · chưa lưu nhãn');
});

test('saved labels, confirmed values and unsaved edits have distinct states', () => {
  assert.equal(readingLabelStatus('LABELED', '00123', '00123'), 'Đã lưu nhãn');
  assert.equal(readingLabelStatus('CONFIRMED', '00123', '00123'), 'Đã xác nhận');
  assert.equal(readingLabelStatus('CONFIRMED', '00123', '00124'), 'Chưa lưu nhãn');
  assert.equal(readingLabelStatus('REJECTED', '00123', '00123'), 'Đã từ chối');
  assert.equal(readingLabelStatus('LABELED', '00123', ''), 'Chưa nhập');
});
