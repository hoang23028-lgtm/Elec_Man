"use client";

import { useEffect, useState } from "react";
import { LatestRequest } from "@/lib/latest-request";

export function useLatestRequest() {
  const [request] = useState(() => new LatestRequest());
  useEffect(() => () => request.invalidate(), [request]);
  return request;
}
