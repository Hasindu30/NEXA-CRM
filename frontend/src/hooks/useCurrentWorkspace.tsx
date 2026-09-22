'use client';

import React, { createContext, useContext } from 'react';
import { Workspace } from '@/types/workspace';

interface CurrentWorkspaceContextType {
  workspace: Workspace;
}

const CurrentWorkspaceContext = createContext<CurrentWorkspaceContextType | undefined>(undefined);

export function CurrentWorkspaceProvider({ 
  workspace, 
  children 
}: { 
  workspace: Workspace, 
  children: React.ReactNode 
}) {
  return (
    <CurrentWorkspaceContext.Provider value={{ workspace }}>
      {children}
    </CurrentWorkspaceContext.Provider>
  );
}

export function useCurrentWorkspace() {
  const context = useContext(CurrentWorkspaceContext);
  if (context === undefined) {
    throw new Error('useCurrentWorkspace must be used within a CurrentWorkspaceProvider');
  }
  return context;
}
