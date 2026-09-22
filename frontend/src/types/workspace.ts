export interface Workspace {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceListResponse {
  data: Workspace[];
}

export interface WorkspaceMember {
  user_id: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  joined_at: string;
}

export interface WorkspaceMemberListResponse {
  data: WorkspaceMember[];
}
