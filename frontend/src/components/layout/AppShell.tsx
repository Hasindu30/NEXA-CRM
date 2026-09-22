'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCurrentWorkspace } from '@/hooks/useCurrentWorkspace';
import { useAuth } from '@/hooks/useAuth';
import { useWorkspace } from '@/hooks/useWorkspace';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { workspace } = useCurrentWorkspace();
  const { workspaces } = useWorkspace();
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const navItems = [
    { name: 'Home', href: `/w/${workspace.slug}` },
    { name: 'People', href: `/w/${workspace.slug}/people` },
    { name: 'Companies', href: `/w/${workspace.slug}/companies` },
    { name: 'Deals', href: `/w/${workspace.slug}/deals`, placeholder: true },
    { name: 'Settings', href: `/w/${workspace.slug}/settings/members` },
  ];

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="h-14 flex items-center px-4 border-b border-gray-200">
          <div className="font-semibold text-gray-900 truncate">{workspace.name}</div>
        </div>
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.name}
                  href={item.placeholder ? '#' : item.href}
                  className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  } ${item.placeholder ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {item.name}
                  {item.placeholder && (
                    <span className="ml-auto text-[10px] uppercase tracking-wider text-gray-400">Soon</span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="h-14 flex items-center justify-between border-b border-gray-200 bg-white px-6">
          <div className="flex items-center space-x-4">
            {/* Workspace switcher placeholder - keeping it simple for now */}
            <select
              className="text-sm border-gray-300 rounded-md py-1 pl-2 pr-8 focus:ring-blue-500 focus:border-blue-500"
              value={workspace.slug}
              onChange={(e) => {
                if (e.target.value !== workspace.slug) {
                  window.location.href = `/w/${e.target.value}`;
                }
              }}
            >
              {workspaces.map(ws => (
                <option key={ws.id} value={ws.slug}>{ws.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button
              onClick={() => logout()}
              className="text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
          <div className="mx-auto max-w-5xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
