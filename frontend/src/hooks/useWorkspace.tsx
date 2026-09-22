'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { Workspace, WorkspaceListResponse } from '@/types/workspace';
import { apiClient } from '@/lib/api';
import { useAuth } from './useAuth';

interface WorkspaceContextType {
  workspaces: Workspace[];
  isLoading: boolean;
  error: string | null;
  refreshWorkspaces: () => Promise<void>;
  getWorkspaceBySlug: (slug: string) => Workspace | undefined;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading: authLoading } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await apiClient<WorkspaceListResponse>('/api/v1/workspaces');
      setWorkspaces(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load workspaces');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Only fetch workspaces if auth is fully restored and user exists
    if (!authLoading) {
      if (user) {
        fetchWorkspaces();
      } else {
        setWorkspaces([]);
        setIsLoading(false);
      }
    }
  }, [authLoading, user]);

  const getWorkspaceBySlug = (slug: string) => {
    return workspaces.find(w => w.slug === slug);
  };

  return (
    <WorkspaceContext.Provider 
      value={{ 
        workspaces, 
        isLoading: authLoading || isLoading, 
        error, 
        refreshWorkspaces: fetchWorkspaces,
        getWorkspaceBySlug
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
