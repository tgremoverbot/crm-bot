import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { broadcastApi } from '../api/broadcasts';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import Badge from '../components/Badge';
import ConfirmModal from '../components/ConfirmModal';
import { Plus, Trash2, Pencil } from 'lucide-react';
import type { Broadcast } from '../types';

const statusVariant: Record<Broadcast['status'], 'gray' | 'yellow' | 'green' | 'red' | 'blue'> = {
  draft: 'gray',
  scheduled: 'yellow',
  sending: 'blue',
  sent: 'green',
  cancelled: 'gray',
  failed: 'red',
};

const deletableStatuses: Broadcast['status'][] = ['draft', 'scheduled', 'failed'];

export default function Broadcasts() {
  const qc = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['broadcasts'],
    queryFn: broadcastApi.list,
  });

  const remove = useMutation({
    mutationFn: (id: string) => broadcastApi.remove(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['broadcasts'] }); setDeleteId(null); },
  });

  return (
    <div className="p-6">
      <PageHeader
        title="Send message"
        subtitle="Send a message to all your students or a specific group"
        action={
          <Link to="/broadcasts/new" className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={14} /> Send to everyone
          </Link>
        }
      />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load broadcasts." />}

      {data && data.length === 0 && (
        <EmptyState title="No broadcasts yet" description="Create a broadcast to send a message to your users." />
      )}

      {data && data.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1a2e24]">
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Name</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Status</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Recipients</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Scheduled</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.map((b) => (
                <tr key={b.id} className="table-row">
                  <td className="px-4 py-3 text-[#dff5ea] font-medium">{b.name}</td>
                  <td className="px-4 py-3">
                    <Badge label={b.status} variant={statusVariant[b.status]} />
                  </td>
                  <td className="px-4 py-3 font-mono text-[#4a7060]">
                    {b.success_count}/{b.recipient_count}
                  </td>
                  <td className="px-4 py-3 text-[#4a7060]">
                    {b.scheduled_at ? new Date(b.scheduled_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-[#4a7060]">{new Date(b.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      {b.status === 'draft' && (
                        <Link
                          to={`/broadcasts/${b.id}/edit`}
                          className="p-1.5 rounded hover:bg-[#1a2e24] text-[#4a7060] hover:text-brand-400 transition-colors"
                        >
                          <Pencil size={14} />
                        </Link>
                      )}
                      {deletableStatuses.includes(b.status) && (
                        <button
                          onClick={() => setDeleteId(b.id)}
                          className="p-1.5 rounded hover:bg-red-900/20 text-[#4a7060] hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {deleteId && (
        <ConfirmModal
          title="Delete broadcast?"
          message="This will permanently delete the broadcast."
          confirmLabel="Delete"
          danger
          onConfirm={() => remove.mutate(deleteId)}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  );
}
