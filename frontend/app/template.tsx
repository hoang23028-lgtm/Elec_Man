import type { ReactNode } from "react";

import { AppFooter } from "@/components/app-footer";

export default function AppTemplate({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <AppFooter />
    </>
  );
}
