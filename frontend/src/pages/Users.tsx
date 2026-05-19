import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { userApi } from '../api/users';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import Badge from '../components/Badge';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZE = 50;

export default function Users() {
  const [page, setPage] = useState(0);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['users', page],
    queryFn: () => userApi.list(PAGE_SIZE, page * PAGE_SIZE),
  });

  return (
    <div className="p-6">
      <PageHeader
        title="Users"
        subtitle="All registered Telegram users"
      />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load users." />}

      {data && (
        <>
          {data.length === 0 && page === 0 ? (
            <EmptyState title="No users yet" description="Users appear here after they start your bot." />
          ) : (
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1a2e24]">
                    <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Name</th>
                    <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Username</th>
                    <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Chat ID</th>
                    <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Status</th>
                    <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((user) => (
                    <tr key={user.id} className="table-row">
                      <td className="px-4 py-3 text-[#dff5ea]">
                        {[user.first_name, user.last_name].filter(Boolean).join(' ') || '—'}
                      </td>
                      <td className="px-4 py-3 text-[#8aab96]">
                        {user.username ? `@${user.username}` : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono text-[#4a7060]">{user.chat_id}</td>
                      <td className="px-4 py-3">
                        {user.is_blocked ? (
                          <Badge label="Blocked" variant="red" />
                        ) : (
                          <Badge label="Active" variant="green" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-[#4a7060]">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between mt-4">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary flex items-center gap-1 text-sm disabled:opacity-40"
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <span className="text-[#4a7060] text-sm">Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={(data?.length ?? 0) < PAGE_SIZE}
              className="btn-secondary flex items-center gap-1 text-sm disabled:opacity-40"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
