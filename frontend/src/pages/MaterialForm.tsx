import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { materialApi } from '../api/materials';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import type { MaterialKind, ParseMode } from '../types';

const KINDS: MaterialKind[] = ['text', 'photo', 'video', 'document', 'link'];
const PARSE_MODES: ParseMode[] = ['HTML', 'MarkdownV2', 'none'];

export default function MaterialForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = !!id;

  const [name, setName] = useState('');
  const [kind, setKind] = useState<MaterialKind>('text');
  const [body, setBody] = useState('');
  const [fileId, setFileId] = useState('');
  const [fileUrl, setFileUrl] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [parseMode, setParseMode] = useState<ParseMode>('HTML');
  const [disablePreview, setDisablePreview] = useState(false);
  const [error, setError] = useState('');

  const { data: existing, isLoading } = useQuery({
    queryKey: ['material', id],
    queryFn: () => materialApi.get(id!),
    enabled: isEdit,
  });

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setKind(existing.kind);
      setBody(existing.body ?? '');
      setFileId(existing.file_id ?? '');
      setFileUrl(existing.file_url ?? '');
      setLinkUrl(existing.link_url ?? '');
      setParseMode(existing.parse_mode ?? 'HTML');
      setDisablePreview(existing.disable_web_page_preview ?? false);
    }
  }, [existing]);

  const create = useMutation({
    mutationFn: materialApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['materials'] }); navigate('/materials'); },
    onError: () => setError('Failed to create material.'),
  });

  const update = useMutation({
    mutationFn: (data: Parameters<typeof materialApi.update>[1]) => materialApi.update(id!, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['materials'] }); navigate('/materials'); },
    onError: () => setError('Failed to update material.'),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const payload = {
      name,
      kind,
      body: body || null,
      file_id: fileId || null,
      file_url: fileUrl || null,
      link_url: linkUrl || null,
      parse_mode: parseMode,
      disable_web_page_preview: disablePreview,
    };
    if (isEdit) { update.mutate(payload); } else { create.mutate(payload); }
  }

  if (isEdit && isLoading) return <div className="p-6"><LoadingState /></div>;

  return (
    <div className="p-6 max-w-xl">
      <PageHeader title={isEdit ? 'Edit Material' : 'New Material'} />

      <form onSubmit={handleSubmit} className="card p-6 space-y-4">
        <div>
          <label className="label">Name</label>
          <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div>
          <label className="label">Kind</label>
          <select className="input-field" value={kind} onChange={(e) => setKind(e.target.value as MaterialKind)}>
            {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Body (text content)</label>
          <textarea className="input-field font-mono text-sm" rows={5} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Message text…" />
        </div>
        {kind !== 'text' && (
          <>
            <div>
              <label className="label">Telegram File ID</label>
              <input className="input-field font-mono text-sm" value={fileId} onChange={(e) => setFileId(e.target.value)} placeholder="AgACAgIAAxkB…" />
            </div>
            <div>
              <label className="label">File URL</label>
              <input className="input-field" type="url" value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} placeholder="https://…" />
            </div>
          </>
        )}
        <div>
          <label className="label">Link URL (optional)</label>
          <input className="input-field" type="url" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://…" />
        </div>
        <div>
          <label className="label">Parse Mode</label>
          <select className="input-field" value={parseMode} onChange={(e) => setParseMode(e.target.value as ParseMode)}>
            {PARSE_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="disable_preview"
            checked={disablePreview}
            onChange={(e) => setDisablePreview(e.target.checked)}
            className="accent-brand-500"
          />
          <label htmlFor="disable_preview" className="text-sm text-[#8aab96]">Disable web page preview</label>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button type="submit" className="btn-primary" disabled={create.isPending || update.isPending}>
            {create.isPending || update.isPending ? 'Saving…' : 'Save'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/materials')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
