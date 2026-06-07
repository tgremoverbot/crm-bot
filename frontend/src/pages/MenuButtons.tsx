import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { menuButtonApi } from '../api/menuButtons';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import ConfirmModal from '../components/ConfirmModal';
import Badge from '../components/Badge';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import type { MenuButton } from '../types';

function rowLabel(row: number) {
  return `Row ${row + 1}`;
}

export default function MenuButtons() {
  const qc = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['menu-buttons'],
    queryFn: menuButtonApi.list,
  });

  const toggle = useMutation({
    mutationFn: (btn: MenuButton) =>
      menuButtonApi.update(btn.id, { is_active: !btn.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['menu-buttons'] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => menuButtonApi.remove(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['menu-buttons'] }); setDeleteId(null); },
  });

  // Group buttons by row for preview
  const preview: Record<number, MenuButton[]> = {};
  if (data) {
    for (const btn of data.filter((b) => b.is_active)) {
      if (!preview[btn.row]) preview[btn.row] = [];
      preview[btn.row].push(btn);
    }
    for (const row of Object.values(preview)) {
      row.sort((a, b) => a.position - b.position);
    }
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Menu buttons"
        subtitle="Buttons shown to users in the Telegram chat"
        action={
          <Link to="/menu-buttons/new" className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={14} /> Add button
          </Link>
        }
      />

      {/* Live keyboard preview */}
      {data && data.some((b) => b.is_active) && (
        <div className="mb-6 p-4 card max-w-sm">
          <p className="text-xs text-[#4a7060] mb-3 uppercase tracking-wider">Live keyboard preview</p>
          <div className="space-y-2">
            {Object.keys(preview).sort().map((r) => (
              <div key={r} className="flex gap-2 flex-wrap">
                {preview[Number(r)].map((btn) => (
                  <span
                    key={btn.id}
                    className="px-3 py-1.5 rounded bg-[#1a2e24] text-[#dff5ea] text-sm border border-[#2a4030]"
                  >
                    {btn.label}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Failed to load menu buttons." />}

      {data && data.length === 0 && (
        <EmptyState
          title="No menu buttons yet"
          description="Add buttons to give users quick access to content."
        />
      )}

      {data && data.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1a2e24]">
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Label</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Row / Position</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Action</th>
                <th className="text-left px-4 py-3 text-[#4a7060] font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.map((btn) => (
                <tr key={btn.id} className="table-row">
                  <td className="px-4 py-3 text-[#dff5ea] font-medium">{btn.label}</td>
                  <td className="px-4 py-3 text-[#4a7060]">
                    {rowLabel(btn.row)}, pos {btn.position}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      label={btn.action_kind === 'material' ? 'Send message' : 'Reply text'}
                      variant={btn.action_kind === 'material' ? 'blue' : 'gray'}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggle.mutate(btn)}
                      className="cursor-pointer"
                    >
                      <Badge
                        label={btn.is_active ? 'Active' : 'Inactive'}
                        variant={btn.is_active ? 'green' : 'gray'}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <Link
                        to={`/menu-buttons/${btn.id}/edit`}
                        className="p-1.5 rounded hover:bg-[#1a2e24] text-[#4a7060] hover:text-brand-400 transition-colors"
                      >
                        <Pencil size={14} />
                      </Link>
                      <button
                        onClick={() => setDeleteId(btn.id)}
                        className="p-1.5 rounded hover:bg-red-900/20 text-[#4a7060] hover:text-red-400 transition-colors"
                      >
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
          title="Delete button?"
          message="This will permanently remove the button from the bot menu."
          confirmLabel="Delete"
          danger
          onConfirm={() => remove.mutate(deleteId)}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  );
}
