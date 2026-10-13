import assert from 'node:assert/strict';
import test from 'node:test';
import { activationIssue } from '../lib/model-activation-gate.ts';

const candidate = (metrics = {}) => ({model_type:'meter_locator_ridge',version:'v1',metrics:{validation_groups_verified:true,validation_images:30,independent_holdout:true,holdout_images:30,end_to_end_evaluated:true,training_run_id:'fixture-run',dataset_hash:'fixture-hash',validation_meter_region_accuracy:.9,holdout_end_to_end:{meter_mean_iou:.9},...metrics}});
test('diagnostic, missing provenance and invalid scores remain disabled', () => {
  for (const metadata of [{independent_holdout:false},{holdout_images:29},{validation_images:'30'},{training_run_id:null},{validation_meter_region_accuracy:NaN},{holdout_end_to_end:{meter_mean_iou:Infinity}}]) assert.ok(activationIssue(candidate(metadata)));
  assert.equal(activationIssue(candidate()),null);
});
test('reader requires crop and full-chain metrics plus compatible active detectors', () => {
  const reader={...candidate(),model_type:'parseq_tiny_finetuned'};
  reader.metrics.holdout_reader={exact_accuracy:.96,coverage:1};
  reader.metrics.holdout_end_to_end={exact_accuracy:.91,coverage:1};
  assert.ok(activationIssue(reader));
  const models=['meter_locator_ridge','reading_region_ridge'].map(model_type=>({model_type,version:'v1',status:'ACTIVE',metrics:{}}));
  assert.equal(activationIssue(reader,models),null);
  reader.metrics.holdout_end_to_end.exact_accuracy=.89;
  assert.ok(activationIssue(reader,models));
});
