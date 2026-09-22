import { ApiErrorData, TokenResponse } from '@/types/auth';

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: ApiErrorData | null
  ) {
    let message = `API Error: ${status}`;
    if (Array.isArray(data?.detail)) {
      message = data.detail.map(e => e.msg).join(', ');
    } else if (typeof data?.detail === 'string') {
      message = data.detail;
    } else if (data?.message) {
      message = data.message;
    }
    super(message);
    this.name = 'ApiError';
  }
}

export function formatApiError(err: any): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  return err?.message || 'An unexpected error occurred';
}

let currentAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  currentAccessToken = token;
}

export function getAccessToken() {
  return currentAccessToken;
}

interface FetchOptions extends RequestInit {
  skipAuthRefresh?: boolean;
}

// Provide a way for AuthProvider to sync its state when apiClient loses the session
export let onAuthFailure: (() => void) | null = null;
export function setOnAuthFailure(callback: () => void) {
  onAuthFailure = callback;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');
if (!BASE_URL) {
  console.error("NEXT_PUBLIC_API_BASE_URL is not defined");
}

async function performRefresh(): Promise<string | null> {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });
    
    if (!response.ok) {
      setAccessToken(null);
      if (onAuthFailure) onAuthFailure();
      return null;
    }
    
    const data: TokenResponse = await response.json();
    setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    setAccessToken(null);
    if (onAuthFailure) onAuthFailure();
    return null;
  }
}

export async function apiClient<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { skipAuthRefresh, ...customOptions } = options;
  const url = `${BASE_URL}${endpoint}`;
  
  const headers = new Headers(customOptions.headers);
  if (currentAccessToken) {
    headers.set('Authorization', `Bearer ${currentAccessToken}`);
  }
  
  // ensure we send cookies (specifically HttpOnly refresh_token cookie)
  const config: RequestInit = {
    ...customOptions,
    headers,
    credentials: 'include',
  };
  
  let response = await fetch(url, config);
  
  // 401 Unauthorized handling
  if (response.status === 401 && !skipAuthRefresh) {
    // Single-flight refresh
    if (!refreshPromise) {
      refreshPromise = performRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    
    const newAccessToken = await refreshPromise;
    if (newAccessToken) {
      // Retry request once
      headers.set('Authorization', `Bearer ${newAccessToken}`);
      config.headers = headers;
      response = await fetch(url, config);
    } else {
      throw new ApiError(401, { message: 'Session expired' });
    }
  }
  
  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // Ignored
    }
    throw new ApiError(response.status, errorData);
  }
  
  if (response.status === 204) {
    return null as unknown as T;
  }
  
  return response.json();
}
