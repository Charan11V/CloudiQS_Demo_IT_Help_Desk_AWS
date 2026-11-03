import { Suspense } from "react";

export default function DemoAccessLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<div className="p-8 text-center text-sm">Loading…</div>}>{children}</Suspense>;
}
