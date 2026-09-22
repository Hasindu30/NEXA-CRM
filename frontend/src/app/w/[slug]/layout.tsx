'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useWorkspace } from '@/hooks/useWorkspace';
import { useAuth } from '@/hooks/useAuth';
import { CurrentWorkspaceProvider } from '@/hooks/useCurrentWorkspace';
import { AppShell } from '@/components/layout/AppShell';

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const slug = params.slug as string;
  const { getWorkspaceBySlug, isLoading: wsLoading } = useWorkspace();
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  if (authLoading || wsLoading) {
    return <div className="flex h-screen items-center justify-center">Loading Workspace...</div>;
  }

  if (!user) {
    router.push('/login');
    return null;
  }

  const workspace = getWorkspaceBySlug(slug);

  if (!workspace) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 flex-col space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Workspace Not Found</h2>
        <p className="text-gray-500">The workspace you are looking for does not exist or you do not have access.</p>
        <button 
          onClick={() => router.push('/w')}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
        >
          Return to Workspace Selection
        </button>
      </div>
    );
  }

  return (
    <CurrentWorkspaceProvider workspace={workspace}>
      <AppShell>
        {children}
      </AppShell>
    </CurrentWorkspaceProvider>
  );
}
