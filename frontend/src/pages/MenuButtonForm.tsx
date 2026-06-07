import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { menuButtonApi } from '../api/menuButtons';
import { materialApi } from '../api/materials';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';

export default function MenuButtonForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = Boolean(id);

  const [label, setLabel] = useState('');
  const [row, setRow] = useState(0);
  const [position, setPosition] = useState(0);
  const [actionKind, setActionKind] = useState<'text' | 'material'>('text');
  const [actionText, setActionText] = useState('');
  const [actionMaterialId, setActionMaterialId] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');

  const { data: existing, isLoading } = useQuery({
    queryKey: ['menu-button', id],
    queryFn: async () => {
      const all = await menuButtonApi.list();
      return all.find((b) => b.id === id) ?? null;
    },
    enabled: isEdit,
  });

  const { data: materials } = useQuery({
    queryKey: ['materials'],
    queryFn: materialApi.list,
  });

  useEffect(() => {
    if (existing) {
      setLabel(existing.label);
      setRow(existing.row);
      setPosition(existing.position);
      setActionKind(existing.action_kind);
      setActionText(existing.action_text ?? '');
      setActionMaterialId(existing.action_material_id ?? '');
      setIsActive(existing.is_active);
    }
  }, [existing]);

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        label,
        row,
        position,
        action_kind: actionKind,
        action_text: actionKind === 'text' ? actionText || null : null,
        action_material_id: actionKind === 'material' ? actionMaterialId || null : null,
        is_active: isActive,
      };
      return isEdit
        ? menuButtonApi.update(id!, payload)
        : menuButtonApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['menu-buttons'] });
      navigate('/menu-buttons');
    },
    onError: () => setError('Failed to save button.'),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!label.trim()) { setError('Label is required.'); return; }
    if (actionKind === 'material' && !actionMaterialId) { setError('Select a message to send.'); return; }
    if (actionKind === 'text' && !actionText.trim()) { setError('Reply text is required.'); return; }
    save.mutate();
  }

  if (isEdit && isLoading) return <div className="p-6"><LoadingState /></div>;

  return (
    <div className="p-6 max-w-lg">
      <PageHeader title={isEdit ? 'Edit button' : 'New menu button'} />

      <form onSubmit={handleSubmit} className="card p-6 space-y-4">
        <div>
          <label className="label">Button label</label>
          <input
            className="input-field"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="📚 Materials"
            required
          />
          <p className="text-xs text-[#4a7060] mt-1">This is exactly what users see and tap in Telegram.</p>
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label className="label">Row</label>
            <input
              type="number"
              min={0}
              className="input-field"
              value={row}
              onChange={(e) => setRow(Number(e.target.value))}
            />
            <p className="text-xs text-[#4a7060] mt-1">Buttons in the same row sit side by side.</p>
          </div>
          <div className="flex-1">
            <label className="label">Position in row</label>
            <input
              type="number"
              min={0}
              className="input-field"
              value={position}
              onChange={(e) => setPosition(Number(e.target.value))}
            />
            <p className="text-xs text-[#4a7060] mt-1">Left to right, starting at 0.</p>
          </div>
        </div>

        <div>
          <label className="label">When tapped, the bot should…</label>
          <select
            className="input-field"
            value={actionKind}
            onChange={(e) => setActionKind(e.target.value as 'text' | 'material')}
          >
            <option value="text">Reply with custom text</option>
            <option value="material">Send a saved message</option>
          </select>
        </div>

        {actionKind === 'text' && (
          <div>
            <label className="label">Reply text</label>
            <textarea
              className="input-field min-h-[80px]"
              value={actionText}
              onChange={(e) => setActionText(e.target.value)}
              placeholder="Hello! Here are the available materials…"
            />
          </div>
        )}

        {actionKind === 'material' && (
          <div>
            <label className="label">Message to send</label>
            <select
              className="input-field"
              value={actionMaterialId}
              onChange={(e) => setActionMaterialId(e.target.value)}
            >
              <option value="">Select message…</option>
              {materials?.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
        )}

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_active"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="accent-brand-400"
          />
          <label htmlFor="is_active" className="text-sm text-[#8aab96]">Active (visible to users)</label>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button type="submit" className="btn-primary text-sm" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Add button'}
          </button>
          <button type="button" className="btn-secondary text-sm" onClick={() => navigate('/menu-buttons')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
