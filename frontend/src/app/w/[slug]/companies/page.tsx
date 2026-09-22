'use client';

import { useState, useEffect } from 'react';
import { useCurrentWorkspace } from '@/hooks/useCurrentWorkspace';
import { apiClient, ApiError } from '@/lib/api';
import { Company, PaginatedCompanyResponse, CompanyCreate, CompanyUpdate } from '@/types/company';
import { useDebounce } from '@/hooks/useDebounce';

export default function CompaniesPage() {
  const { workspace } = useCurrentWorkspace();
  
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(50);
  const [search, setSearch] = useState('');
  
  const debouncedSearch = useDebounce(search, 300);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({ name: '', domain: '', phone: '', website: '' });
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchCompanies = async (currentPage: number, currentSearch: string) => {
    try {
      setIsLoading(true);
      setError('');
      
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', limit.toString());
      if (currentSearch.trim()) {
        params.append('q', currentSearch.trim());
      }
      
      const data = await apiClient<PaginatedCompanyResponse>(`/api/v1/workspaces/${workspace.id}/companies?${params.toString()}`);
      setCompanies(data.data);
      setTotal(data.meta.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load companies');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setPage(1); // Reset page on search change
  }, [debouncedSearch]);

  useEffect(() => {
    fetchCompanies(page, debouncedSearch);
  }, [workspace.id, page, debouncedSearch]);

  const handleOpenModal = (company?: Company) => {
    if (company) {
      setEditingCompany(company);
      setFormData({
        name: company.name,
        domain: company.domain || '',
        phone: company.phone || '',
        website: company.website || ''
      });
    } else {
      setEditingCompany(null);
      setFormData({ name: '', domain: '', phone: '', website: '' });
    }
    setFormError('');
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);
    
    // Normalize empty strings to null for optional fields to keep DB clean
    const payload = {
      name: formData.name,
      domain: formData.domain.trim() || null,
      phone: formData.phone.trim() || null,
      website: formData.website.trim() || null
    };

    try {
      if (editingCompany) {
        await apiClient(`/api/v1/workspaces/${workspace.id}/companies/${editingCompany.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await apiClient(`/api/v1/workspaces/${workspace.id}/companies`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      handleCloseModal();
      await fetchCompanies(page, debouncedSearch);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setFormError(typeof err.data?.detail === 'string' ? err.data.detail : err.message);
      } else {
        setFormError('Failed to save company');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (companyId: string) => {
    if (!window.confirm('Are you sure you want to delete this company?')) return;
    try {
      await apiClient(`/api/v1/workspaces/${workspace.id}/companies/${companyId}`, {
        method: 'DELETE'
      });
      await fetchCompanies(page, debouncedSearch);
    } catch (err: any) {
      if (err instanceof ApiError) {
        alert(typeof err.data?.detail === 'string' ? err.data.detail : err.message);
      } else {
        alert('Failed to delete company');
      }
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-gray-200 pb-5">
        <h3 className="text-2xl font-semibold leading-6 text-gray-900">Companies</h3>
        <button
          onClick={() => handleOpenModal()}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
        >
          Add Company
        </button>
      </div>

      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-sm">
          <input
            type="text"
            className="block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
            placeholder="Search companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {error && <div className="text-red-600">{error}</div>}

      <div className="rounded-lg bg-white shadow-sm ring-1 ring-gray-900/5 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-300">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Name</th>
              <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Domain</th>
              <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Phone</th>
              <th className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {isLoading ? (
              <tr><td colSpan={4} className="py-8 text-center text-gray-500">Loading...</td></tr>
            ) : companies.length === 0 ? (
              <tr><td colSpan={4} className="py-8 text-center text-gray-500">No companies found.</td></tr>
            ) : (
              companies.map((company) => (
                <tr key={company.id}>
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                    {company.name}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{company.domain || '-'}</td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{company.phone || '-'}</td>
                  <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <button onClick={() => handleOpenModal(company)} className="text-blue-600 hover:text-blue-900 mr-4">Edit</button>
                    <button onClick={() => handleDelete(company.id)} className="text-red-600 hover:text-red-900">Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-lg shadow-sm ring-1 ring-gray-900/5">
          <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{(page - 1) * limit + 1}</span> to <span className="font-medium">{Math.min(page * limit, total)}</span> of <span className="font-medium">{total}</span> results
              </p>
            </div>
            <div>
              <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={handleCloseModal}></div>
            <div className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
              <form onSubmit={handleSubmit}>
                <div>
                  <h3 className="text-base font-semibold leading-6 text-gray-900">
                    {editingCompany ? 'Edit Company' : 'Add Company'}
                  </h3>
                  <div className="mt-4 space-y-4">
                    <div>
                      <label htmlFor="name" className="block text-sm font-medium leading-6 text-gray-900">Name *</label>
                      <input
                        type="text"
                        name="name"
                        id="name"
                        required
                        className="mt-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                        value={formData.name}
                        onChange={(e) => setFormData({...formData, name: e.target.value})}
                      />
                    </div>
                    <div>
                      <label htmlFor="domain" className="block text-sm font-medium leading-6 text-gray-900">Domain</label>
                      <input
                        type="text"
                        name="domain"
                        id="domain"
                        className="mt-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                        value={formData.domain}
                        onChange={(e) => setFormData({...formData, domain: e.target.value})}
                      />
                    </div>
                    <div>
                      <label htmlFor="phone" className="block text-sm font-medium leading-6 text-gray-900">Phone</label>
                      <input
                        type="text"
                        name="phone"
                        id="phone"
                        className="mt-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                        value={formData.phone}
                        onChange={(e) => setFormData({...formData, phone: e.target.value})}
                      />
                    </div>
                    <div>
                      <label htmlFor="website" className="block text-sm font-medium leading-6 text-gray-900">Website</label>
                      <input
                        type="url"
                        name="website"
                        id="website"
                        className="mt-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                        value={formData.website}
                        onChange={(e) => setFormData({...formData, website: e.target.value})}
                      />
                    </div>
                  </div>
                </div>
                {formError && <div className="mt-4 text-sm text-red-600">{formError}</div>}
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 sm:col-start-2 disabled:opacity-50"
                  >
                    {isSubmitting ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
