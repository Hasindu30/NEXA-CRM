export interface CompanySummary {
  id: string;
  name: string;
}

export interface Person {
  id: string;
  workspace_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  company_id: string | null;
  company: CompanySummary | null;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface PaginatedPersonResponse {
  data: Person[];
  meta: PaginationMeta;
}
