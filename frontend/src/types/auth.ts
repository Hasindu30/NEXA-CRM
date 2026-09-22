export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  user?: User;
}

export interface MessageResponse {
  message: string;
}

export interface ApiErrorData {
  detail?: string | Array<{ msg: string; loc: string[] }>;
  message?: string;
}
