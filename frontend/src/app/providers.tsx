'use client';

import { AuthProvider } from '@/hooks/useAuth';
import { WorkspaceProvider } from '@/hooks/useWorkspace';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        {children}
      </WorkspaceProvider>
    </AuthProvider>
  );
}
