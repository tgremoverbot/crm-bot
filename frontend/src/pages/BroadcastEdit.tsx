import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { broadcastApi } from '../api/broadcasts';
import { materialApi } from '../api/materials';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { Users, Send, Save } from 'lucide-react';

export default function BroadcastEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [name, setName] = useState('');
  const [materialId, setMaterialId] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const { data: bc, isLoading, isError } = useQuery({
    queryKey: ['broadcast', id],
    queryFn: () => broadcastApi.get(id!),
    enabled: !!id,
  });

  const { data: materials } = useQuery({
    queryKey: ['materials'],
    queryFn: materialApi.list,
  });

  useEffect(() => {
    if (bc) {
      setName(bc.name);
      setMaterialId(bc.material_id);
      setScheduledAt(bc.scheduled_at ? new Date(bc.scheduled_at).toISOString().slice(0, 16) : '');
    }
  }, [bc]);

  const preview = useMutation({
    mutationFn: () => broadcastApi.preview(bc?.segment_id ?? null),
    onSuccess: (data) => setPreviewCount(data.recipient_count),
    onError: () => setError('Failed to get recipient count.'),
  });

  const save = useMutation({
    mutationFn: () =>
      broadcastApi.update(id!, {
        name,
        material_id: materialId,
        segment_id: bc?.segment_id ?? null,
        scheduled_at: scheduledAt || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['broadcasts'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
    onError: () => setError('Failed to save changes.'),
  });

  const send = useMutation({
    mutationFn: async () => {
      await broadcastApi.update(id!, {
        name,
        material_id: materialId,
        segment_id: bc?.segment_id ?? null,
        scheduled_at: scheduledAt || null,
      });
      return broadcastApi.send(id!, scheduledAt || null);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['broadcasts'] });
      navigate('/broadcasts');
    },
    onError: () => setError('Failed to send broadcast.'),
  });

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!name || !materialId) { setError('Name and message are required.'); return; }
    save.mutate();
  }

  function handleSend() {
    setError('');
    if (!name || !materialId) { setError('Name and message are required.'); return; }
    send.mutate();
  }

  if (isLoading) return <div className="p-6"><LoadingState /></div>;
  if (isError || !bc) return <div className="p-6"><ErrorState message="Broadcast not found." /></div>;

  if (bc.status !== 'draft') {
    return (
      <div className="p-6 max-w-xl">
        <PageHeader title="Broadcast" />
        <div className="card p-6 text-[#4a7060] text-sm">
          This broadcast is in <span className="text-[#dff5ea] font-medium">{bc.status}</span> status and cannot be edited.
        </div>
      </div>
    );
  }

  const selectedMaterial = materials?.find((m) => m.id === materialId);

  return (
    <div className="p-6 max-w-xl">
      <PageHeader title="Edit draft broadcast" />

      <form onSubmit={handleSave} className="card p-6 space-y-4">
        <div>
          <label className="label">Message name</label>
          <input
            className="input-field"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="May announcement"
          />
        </div>

        <div>
          <label className="label">Message to send</label>
          <select
            className="input-field"
            value={materialId}
            onChange={(e) => setMaterialId(e.target.value)}
            required
          >
            <option value="">Select message…</option>
            {materials?.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          {selectedMaterial?.body && (
            <p className="text-xs text-[#4a7060] mt-1 truncate">{selectedMaterial.body.slice(0, 80)}</p>
          )}
        </div>

        <div>
          <label className="label">Send at (optional)</label>
          <input
            type="datetime-local"
            className="input-field"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
          />
          <p className="text-xs text-[#4a7060] mt-1">Leave empty to send immediately.</p>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}
        {saved && <p className="text-brand-400 text-sm">Saved.</p>}

        <div className="flex gap-3 pt-2 flex-wrap">
          <button
            type="submit"
            className="btn-secondary flex items-center gap-2 text-sm"
            disabled={save.isPending}
          >
            <Save size={14} /> {save.isPending ? 'Saving…' : 'Save draft'}
          </button>

          <button
            type="button"
            className="btn-secondary flex items-center gap-2 text-sm"
            onClick={() => { setError(''); preview.mutate(); }}
            disabled={preview.isPending}
          >
            <Users size={14} /> {preview.isPending ? 'Checking…' : 'Check recipients'}
          </button>
        </div>

        {previewCount !== null && (
          <div className="flex items-center gap-3 p-3 bg-brand-500/10 rounded-lg border border-brand-500/20">
            <Users size={16} className="text-brand-400 shrink-0" />
            <p className="text-sm text-[#dff5ea]">
              <span className="font-bold font-mono">{previewCount.toLocaleString()}</span> people will receive this message
            </p>
          </div>
        )}

        <div className="pt-1 border-t border-[#1a2e24]">
          <button
            type="button"
            className="btn-primary flex items-center gap-2 text-sm w-full justify-center mt-3"
            onClick={handleSend}
            disabled={send.isPending}
          >
            <Send size={14} /> {send.isPending ? 'Sending…' : scheduledAt ? 'Schedule send' : 'Send now'}
          </button>
        </div>
      </form>
    </div>
  );
}
