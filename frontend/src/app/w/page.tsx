'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useWorkspace } from '@/hooks/useWorkspace';
import { useAuth } from '@/hooks/useAuth';

export default function WorkspaceBootstrapPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const { workspaces, isLoading: wsLoading } = useWorkspace();

  useEffect(() => {
    if (authLoading || wsLoading) return;

    if (!user) {
      router.push('/login');
      return;
    }

    if (workspaces.length === 0) {
      router.push('/workspaces/create');
    } else if (workspaces.length === 1) {
      router.push(`/w/${workspaces[0].slug}`);
    }
    // If >1, stay on this page to show the selector
  }, [authLoading, wsLoading, user, workspaces, router]);

  if (authLoading || wsLoading) {
    return <div className="flex min-h-screen items-center justify-center">Loading...</div>;
  }

  if (!user) return null;
  if (workspaces.length <= 1) return <div className="flex min-h-screen items-center justify-center">Redirecting...</div>;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-6 rounded-lg bg-white p-8 shadow">
        <h2 className="text-center text-2xl font-bold text-gray-900">Select Workspace</h2>
        <div className="space-y-3">
          {workspaces.map(ws => (
            <button
              key={ws.id}
              onClick={() => router.push(`/w/${ws.slug}`)}
              className="w-full text-left rounded-md border border-gray-300 p-4 hover:border-blue-500 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <div className="font-medium text-gray-900">{ws.name}</div>
              <div className="text-sm text-gray-500">{ws.slug}</div>
            </button>
          ))}
        </div>
        <div className="pt-4 border-t border-gray-200">
          <button
            onClick={() => router.push('/workspaces/create')}
            className="w-full rounded-md border border-transparent bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-200"
          >
            Create New Workspace
          </button>
        </div>
      </div>
    </div>
  );
}
