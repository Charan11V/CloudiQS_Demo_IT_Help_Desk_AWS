'use client';

import { AlertCircle } from 'lucide-react';

export default function DemoModeBanner() {
  return (
    <div className="bg-amber-100 border-b-2 border-amber-300 px-4 py-2">
      <div className="max-w-7xl mx-auto flex items-center gap-2 text-amber-900">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <span className="font-semibold text-sm">
          DEMO MODE: This system uses simulated enterprise systems and data
        </span>
      </div>
    </div>
  );
}
