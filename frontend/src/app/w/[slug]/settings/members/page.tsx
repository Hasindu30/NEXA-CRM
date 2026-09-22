'use client';

import { useState, useEffect } from 'react';
import { useCurrentWorkspace } from '@/hooks/useCurrentWorkspace';
import { useAuth } from '@/hooks/useAuth';
import { apiClient, ApiError } from '@/lib/api';
import { WorkspaceMember, WorkspaceMemberListResponse } from '@/types/workspace';

export default function MembersPage() {
  const { workspace } = useCurrentWorkspace();
  const { user } = useAuth();
  
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Add member state
  const [newEmail, setNewEmail] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState('');

  const fetchMembers = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await apiClient<WorkspaceMemberListResponse>(`/api/v1/workspaces/${workspace.id}/members`);
      setMembers(data.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load members');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, [workspace.id]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError('');
    setIsAdding(true);
    try {
      await apiClient(`/api/v1/workspaces/${workspace.id}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: newEmail })
      });
      setNewEmail('');
      await fetchMembers();
    } catch (err: any) {
      if (err instanceof ApiError) {
        setAddError(typeof err.data?.detail === 'string' ? err.data.detail : err.message);
      } else {
        setAddError('Failed to add member');
      }
    } finally {
      setIsAdding(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await apiClient(`/api/v1/workspaces/${workspace.id}/members/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      await fetchMembers();
    } catch (err: any) {
      alert(err.message || 'Failed to change role');
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!window.confirm('Are you sure you want to remove this member?')) return;
    try {
      await apiClient(`/api/v1/workspaces/${workspace.id}/members/${userId}`, {
        method: 'DELETE'
      });
      await fetchMembers();
    } catch (err: any) {
      if (err instanceof ApiError) {
        alert(typeof err.data?.detail === 'string' ? err.data.detail : err.message);
      } else {
        alert('Failed to remove member');
      }
    }
  };

  const currentMember = members.find(m => m.user_id === user?.id);
  const currentUserRole = currentMember?.role || 'member';

  const canAddMembers = currentUserRole === 'owner' || currentUserRole === 'admin';

  if (isLoading) return <div>Loading members...</div>;
  if (error) return <div className="text-red-600">{error}</div>;

  return (
    <div className="space-y-8">
      <div className="border-b border-gray-200 pb-5">
        <h3 className="text-2xl font-semibold leading-6 text-gray-900">Workspace Members</h3>
      </div>

      {canAddMembers && (
        <div className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-900/5">
          <h4 className="text-base font-semibold leading-6 text-gray-900">Add Member</h4>
          <form className="mt-4 flex items-center space-x-4" onSubmit={handleAddMember}>
            <div className="flex-1 max-w-sm">
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                type="email"
                name="email"
                id="email"
                required
                className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
                placeholder="colleague@example.com"
                value={newEmail}
                onChange={e => setNewEmail(e.target.value)}
              />
            </div>
            <button
              type="submit"
              disabled={isAdding}
              className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50"
            >
              {isAdding ? 'Adding...' : 'Add'}
            </button>
          </form>
          {addError && <p className="mt-2 text-sm text-red-600">{addError}</p>}
        </div>
      )}

      <div className="rounded-lg bg-white shadow-sm ring-1 ring-gray-900/5 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-300">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Email</th>
              <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Role</th>
              <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Joined</th>
              <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {members.map((member) => {
              const isSelf = member.user_id === user?.id;
              
              // Determine if current user can modify this specific member
              let canModify = false;
              let roleOptions = ['member']; // Default fallback

              if (currentUserRole === 'owner') {
                if (!isSelf) {
                  canModify = true;
                  roleOptions = ['owner', 'admin', 'member'];
                }
              } else if (currentUserRole === 'admin') {
                if (!isSelf && member.role !== 'owner') {
                  canModify = true;
                  roleOptions = ['admin', 'member'];
                }
              }

              return (
                <tr key={member.user_id}>
                  <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                    {member.email}
                    {isSelf && <span className="ml-2 inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">You</span>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {canModify ? (
                      <select
                        value={member.role}
                        onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                        className="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-blue-600 sm:text-sm sm:leading-6"
                      >
                        {roleOptions.map(r => (
                          <option key={r} value={r}>
                            {r.charAt(0).toUpperCase() + r.slice(1)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="capitalize">{member.role}</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {new Date(member.joined_at).toLocaleDateString()}
                  </td>
                  <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    {canModify && (
                      <button
                        onClick={() => handleRemoveMember(member.user_id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
