export interface Company {
  id: string;
  workspace_id: string;
  name: string;
  domain: string | null;
  phone: string | null;
  website: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface PaginatedCompanyResponse {
  data: Company[];
  meta: PaginationMeta;
}

export interface CompanyCreate {
  name: string;
  domain?: string | null;
  phone?: string | null;
  website?: string | null;
}

export interface CompanyUpdate {
  name?: string;
  domain?: string | null;
  phone?: string | null;
  website?: string | null;
}
