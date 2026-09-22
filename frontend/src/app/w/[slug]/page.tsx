'use client';

import { useCurrentWorkspace } from '@/hooks/useCurrentWorkspace';

export default function WorkspaceHomePage() {
  const { workspace } = useCurrentWorkspace();

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-5">
        <h3 className="text-2xl font-semibold leading-6 text-gray-900">Dashboard</h3>
      </div>
      <div className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-900/5">
        <h4 className="text-lg font-medium text-gray-900">Welcome to {workspace.name}</h4>
        <p className="mt-2 text-gray-500">
          This is a placeholder for the CRM dashboard.
        </p>
      </div>
    </div>
  );
}
