import assert from 'node:assert/strict';
import test from 'node:test';
import { trainingStatusLabel } from '../lib/training-status.ts';

test('training states share Vietnamese labels and do not expose unknown codes', () => {
  for (const [state, label] of Object.entries({PENDING:'Đang chờ', RUNNING:'Đang huấn luyện', COMPLETED:'Hoàn tất', FAILED:'Thất bại', CANCELLED:'Đã hủy'})) {
    assert.equal(trainingStatusLabel(state), label);
  }
  assert.equal(trainingStatusLabel('UNRECOGNIZED'), 'Chưa rõ trạng thái');
});
