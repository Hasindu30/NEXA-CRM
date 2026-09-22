'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, TokenResponse } from '@/types/auth';
import { apiClient, setAccessToken, setOnAuthFailure } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (tokenResponse: TokenResponse) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Initial session restore
    let isMounted = true;
    
    const restoreSession = async () => {
      try {
        // Attempt refresh using HttpOnly cookie
        const data = await apiClient<TokenResponse>('/api/v1/auth/refresh', {
          method: 'POST',
          skipAuthRefresh: true,
        });
        
        setAccessToken(data.access_token);
        
        // Fetch current user details since /refresh only returns token
        const me = await apiClient<User>('/api/v1/auth/me', {
          skipAuthRefresh: true,
        });
        
        if (isMounted) setUser(me);
      } catch (err) {
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    
    restoreSession();

    // Register callback for API client refresh failures during active session
    setOnAuthFailure(() => {
      if (isMounted) {
        setUser(null);
        router.push('/login');
      }
    });
    
    return () => {
      isMounted = false;
      setOnAuthFailure(() => {});
    };
  }, [router]);

  const login = (tokenResponse: TokenResponse) => {
    setAccessToken(tokenResponse.access_token);
    if (tokenResponse.user) {
      setUser(tokenResponse.user);
    }
  };

  const logout = async () => {
    try {
      await apiClient('/api/v1/auth/logout', {
        method: 'POST',
        skipAuthRefresh: true,
      });
    } catch {
      // Ignore errors on logout
    } finally {
      setAccessToken(null);
      setUser(null);
      router.push('/login');
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
