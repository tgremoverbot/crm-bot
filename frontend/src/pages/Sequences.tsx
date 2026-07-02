import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { sequenceApi } from '../api/sequences';
import { settingsApi } from '../api/settings';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import Badge from '../components/Badge';
import ConfirmModal from '../components/ConfirmModal';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import type { Sequence } from '../types';

function DefaultFlowCard({ sequences }: { sequences: Sequence[] }) {
  const qc = useQueryClient();
  const [value, setValue] = useState('');
  const [saved, setSaved] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  });

  useEffect(() => {
    if (settings) setValue(settings.default_sequence_id ?? '');
  }, [settings]);

  const save = useMutation({
    mutationFn: (sequenceId: string | null) => settingsApi.update(sequenceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (isLoading) return null;

  return (
    <div className="card p-5 mb-6">
      <h3 className="text-sm font-semibold text-[#dff5ea] mb-1">Default auto-flow</h3>
      <p className="text-xs text-[#4a7060] mb-3">
        Sent automatically to people who start the bot without any invite link.
      </p>
      <div className="flex gap-3 items-center flex-wrap">
        <select
          className="input-field max-w-xs"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        >
          <option value="">None</option>
          {sequences.filter((s) => s.is_active).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button
          type="button"
          className="btn-secondary text-sm"
          disabled={save.isPending}
          onClick={() => save.mutate(value || null)}
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </button>
        {saved && <span className="text-brand-400 text-sm">Saved.</span>}
      </div>
    </div>
  );
}

export default function Sequences() {
  const qc = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sequences'],
    queryFn: sequenceApi.list,
  });

  const remove = useMutation({
    mutationFn: (id: string) => sequenceApi.remove(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sequences'] }); setDeleteId(null); },
  });

  return (
    <div className="p-6">
      <PageHeader
        title="Auto-flows"
        subtitle="Automated message drip auto-flows"
        action={
          <Link to="/sequences/new" className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={14} /> New Auto-flow
          </Link>
        }
      />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load sequences." />}

      {data && data.length > 0 && <DefaultFlowCard sequences={data} />}

      {data && data.length === 0 && (
        <EmptyState title="No auto-flows yet" description="Create an auto-flow to automate follow-up messages." />
      )}

      {data && data.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1a2e24]">
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Name</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Status</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id} className="table-row">
                  <td className="px-4 py-3 text-[#dff5ea] font-medium">{s.name}</td>
                  <td className="px-4 py-3">
                    <Badge label={s.is_active ? 'Active' : 'Inactive'} variant={s.is_active ? 'green' : 'gray'} />
                  </td>
                  <td className="px-4 py-3 text-[#4a7060]">{new Date(s.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <Link to={`/sequences/${s.id}/edit`} className="p-1.5 rounded hover:bg-[#1a2e24] text-[#4a7060] hover:text-brand-400 transition-colors">
                        <Pencil size={14} />
                      </Link>
                      <button onClick={() => setDeleteId(s.id)} className="p-1.5 rounded hover:bg-red-900/20 text-[#4a7060] hover:text-red-400 transition-colors">
                        <Trash2 size={14} />
                      </button>
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
          title="Delete auto-flow?"
          message="This will permanently delete the auto-flow. Existing scheduled messages will still be sent."
          confirmLabel="Delete"
          danger
          onConfirm={() => remove.mutate(deleteId)}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  );
}
