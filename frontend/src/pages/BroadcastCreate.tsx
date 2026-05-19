import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { broadcastApi } from '../api/broadcasts';
import { materialApi } from '../api/materials';
import { sequenceApi } from '../api/sequences';
import PageHeader from '../components/PageHeader';
import { Users, Send, Eye } from 'lucide-react';

type Step = 'compose' | 'preview' | 'send';

export default function BroadcastCreate() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [step, setStep] = useState<Step>('compose');
  const [name, setName] = useState('');
  const [materialId, setMaterialId] = useState('');
  const [segmentId, setSegmentId] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [broadcastId, setBroadcastId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const { data: materials } = useQuery({ queryKey: ['materials'], queryFn: materialApi.list });
  const { data: sequences } = useQuery({ queryKey: ['sequences'], queryFn: sequenceApi.list });

  const preview = useMutation({
    mutationFn: () => broadcastApi.preview(segmentId || null),
    onSuccess: (data) => {
      setPreviewCount(data.recipient_count);
      setStep('preview');
    },
    onError: () => setError('Failed to get preview.'),
  });

  const create = useMutation({
    mutationFn: () =>
      broadcastApi.create({
        name,
        material_id: materialId,
        segment_id: segmentId || null,
        scheduled_at: scheduledAt || null,
      }),
    onSuccess: (data) => {
      setBroadcastId(data.id);
      setStep('send');
    },
    onError: () => setError('Failed to create broadcast.'),
  });

  const send = useMutation({
    mutationFn: () => broadcastApi.send(broadcastId!, scheduledAt || null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['broadcasts'] });
      navigate('/broadcasts');
    },
    onError: () => setError('Failed to send broadcast.'),
  });

  function handlePreview(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!name || !materialId) { setError('Name and material are required.'); return; }
    preview.mutate();
  }

  const stepLabels: Record<Step, string> = {
    compose: '1. Compose',
    preview: '2. Preview',
    send: '3. Send',
  };

  return (
    <div className="p-6 max-w-xl">
      <PageHeader title="New Broadcast" />

      <div className="flex gap-6 mb-6">
        {(['compose', 'preview', 'send'] as Step[]).map((s) => (
          <span
            key={s}
            className={`text-sm font-medium ${step === s ? 'text-brand-400' : 'text-[#2a4030]'}`}
          >
            {stepLabels[s]}
          </span>
        ))}
      </div>

      {step === 'compose' && (
        <form onSubmit={handlePreview} className="card p-6 space-y-4">
          <div>
            <label className="label">Broadcast Name</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required placeholder="May announcement" />
          </div>
          <div>
            <label className="label">Material</label>
            <select className="input-field" value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
              <option value="">Select material…</option>
              {materials?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Segment (optional)</label>
            <select className="input-field" value={segmentId} onChange={(e) => setSegmentId(e.target.value)}>
              <option value="">All active users</option>
              {sequences?.map((s) => <option key={s.id} value={s.id}>Enrolled in: {s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Schedule At (optional)</label>
            <input
              type="datetime-local"
              className="input-field"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
            />
            <p className="text-xs text-[#4a7060] mt-1">Leave empty to send immediately after confirmation.</p>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn-primary flex items-center gap-2" disabled={preview.isPending}>
              <Eye size={14} /> {preview.isPending ? 'Checking…' : 'Preview Recipients'}
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate('/broadcasts')}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {step === 'preview' && (
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-4 p-4 bg-brand-500/10 rounded-lg border border-brand-500/20">
            <Users size={20} className="text-brand-400 shrink-0" />
            <div>
              <p className="text-2xl font-bold text-[#dff5ea] font-mono">{previewCount?.toLocaleString()}</p>
              <p className="text-sm text-[#4a7060]">recipients will receive this broadcast</p>
            </div>
          </div>

          <div className="text-sm space-y-2 text-[#8aab96]">
            <p><span className="text-[#4a7060]">Name:</span> {name}</p>
            <p><span className="text-[#4a7060]">Material:</span> {materials?.find((m) => m.id === materialId)?.name}</p>
            <p><span className="text-[#4a7060]">Segment:</span> {segmentId ? sequences?.find((s) => s.id === segmentId)?.name : 'All active users'}</p>
            {scheduledAt && <p><span className="text-[#4a7060]">Scheduled:</span> {new Date(scheduledAt).toLocaleString()}</p>}
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3">
            <button
              className="btn-primary flex items-center gap-2"
              onClick={() => create.mutate()}
              disabled={create.isPending}
            >
              <Send size={14} /> {create.isPending ? 'Creating…' : 'Create Broadcast'}
            </button>
            <button className="btn-secondary" onClick={() => setStep('compose')}>Back</button>
          </div>
        </div>
      )}

      {step === 'send' && (
        <div className="card p-6 space-y-5">
          <div className="p-4 bg-brand-500/10 rounded-lg border border-brand-500/20">
            <p className="text-sm text-brand-400 font-medium">Broadcast created successfully</p>
            <p className="text-xs text-[#4a7060] mt-1">Click Send to dispatch it now{scheduledAt ? ' at the scheduled time' : ''}.</p>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3">
            <button
              className="btn-primary flex items-center gap-2"
              onClick={() => send.mutate()}
              disabled={send.isPending}
            >
              <Send size={14} /> {send.isPending ? 'Sending…' : scheduledAt ? 'Schedule Send' : 'Send Now'}
            </button>
            <button className="btn-secondary" onClick={() => navigate('/broadcasts')}>
              Save as Draft
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
