import assert from "node:assert/strict";
import test from "node:test";
import { structuralEqual } from "../lib/structural-equal.ts";

test("unchanged geometry is not reported as a correction", () => {
  assert.equal(structuralEqual({ points: [{ x: 0.2, y: 0.4 }] }, { points: [{ y: 0.4, x: 0.2 }] }), true);
  assert.equal(structuralEqual([0.1, 0.2], [0.1, 0.3]), false);
  assert.equal(structuralEqual(null, { points: [] }), false);
  assert.equal(structuralEqual(undefined, null), false);
  assert.equal(structuralEqual([], {}), false);
  assert.equal(structuralEqual({ x: 0, y: undefined }, { x: 0 }), false);
});
