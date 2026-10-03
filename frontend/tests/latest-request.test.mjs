import assert from "node:assert/strict";
import test from "node:test";
import { LatestRequest } from "../lib/latest-request.ts";

test("the newest response wins when requests finish out of order", () => {
  const requests = new LatestRequest();
  const previous = requests.begin();
  const next = requests.begin();
  assert.equal(requests.isCurrent(previous), false);
  assert.equal(requests.isCurrent(next), true);
});

test("switching selection invalidates pending work before the next request", () => {
  const requests = new LatestRequest();
  const pending = requests.begin();
  requests.invalidate();
  assert.equal(requests.isCurrent(pending), false);
  assert.equal(requests.isCurrent(requests.begin()), true);
});
