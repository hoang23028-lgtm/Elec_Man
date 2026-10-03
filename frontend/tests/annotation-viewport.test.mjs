import { test } from 'node:test';
import assert from 'node:assert/strict';
import { polygonBounds, regionViewport } from '../lib/annotation-viewport.ts';

test('meter region is enlarged and centered without changing its coordinates', () => {
  const box = { x: .2, y: .3, width: .4, height: .25 };
  const original = JSON.stringify(box);
  const target = regionViewport(box, 300, .5, 700, 600);
  assert.ok(target.zoom > 2);
  assert.ok(Math.abs((box.y + box.height / 2) * 600 * target.zoom - target.top - 300) < .001);
  assert.equal(JSON.stringify(box), original);
});
test('edge regions stay within scroll bounds and tiny regions have bounded zoom', () => {
  const target = regionViewport({x:0,y:0,width:.001,height:.001}, 300, .5, 700, 600);
  assert.equal(target.zoom, 12);
  assert.equal(target.left, 0);
  assert.equal(target.top, 0);
});
test('invalid boxes never produce infinite zoom or scroll', () => {
  for (const box of [{x:0,y:0,width:0,height:.3}, {x:NaN,y:0,width:.2,height:.3}, {x:.9,y:0,width:.2,height:.3}]) {
    assert.equal(regionViewport(box,300,.5,700,600), null);
  }
});
test('four corner labels give normalized bounds', () => {
  assert.equal(polygonBounds(null), null);
  assert.deepEqual(polygonBounds({points:[{x:0,y:0},{x:1,y:0},{x:1,y:1},{x:0,y:1}]}), {x:0,y:0,width:1,height:1});
});
