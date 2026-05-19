import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignApi } from '../api/campaigns';
import { sequenceApi } from '../api/sequences';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';

export default function CampaignForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = !!id;

  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [defaultSequenceId, setDefaultSequenceId] = useState('');
  const [error, setError] = useState('');

  const { data: existing, isLoading } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignApi.get(id!),
    enabled: isEdit,
  });

  const { data: sequences } = useQuery({
    queryKey: ['sequences'],
    queryFn: sequenceApi.list,
  });

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setSlug(existing.slug);
      setDescription(existing.description ?? '');
      setIsActive(existing.is_active);
      setDefaultSequenceId(existing.default_sequence_id ?? '');
    }
  }, [existing]);

  const create = useMutation({
    mutationFn: campaignApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); navigate('/campaigns'); },
    onError: () => setError('Failed to create campaign.'),
  });

  const update = useMutation({
    mutationFn: ({ data }: { data: Parameters<typeof campaignApi.update>[1] }) =>
      campaignApi.update(id!, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); navigate('/campaigns'); },
    onError: () => setError('Failed to update campaign.'),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const payload = {
      name,
      slug,
      description: description || null,
      is_active: isActive,
      default_sequence_id: defaultSequenceId || null,
    };
    if (isEdit) {
      update.mutate({ data: payload });
    } else {
      create.mutate(payload);
    }
  }

  if (isEdit && isLoading) return <div className="p-6"><LoadingState /></div>;

  return (
    <div className="p-6 max-w-xl">
      <PageHeader title={isEdit ? 'Edit Campaign' : 'New Campaign'} />

      <form onSubmit={handleSubmit} className="card p-6 space-y-4">
        <div>
          <label className="label">Name</label>
          <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div>
          <label className="label">Slug</label>
          <input className="input-field font-mono" value={slug} onChange={(e) => setSlug(e.target.value)} required placeholder="my-campaign" />
          <p className="text-xs text-[#4a7060] mt-1">Used in Telegram deep-link: ?start=slug</p>
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input-field" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label className="label">Default Sequence (optional)</label>
          <select
            className="input-field"
            value={defaultSequenceId}
            onChange={(e) => setDefaultSequenceId(e.target.value)}
          >
            <option value="">None</option>
            {sequences?.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_active"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="accent-brand-500"
          />
          <label htmlFor="is_active" className="text-sm text-[#8aab96]">Active</label>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button type="submit" className="btn-primary" disabled={create.isPending || update.isPending}>
            {create.isPending || update.isPending ? 'Saving…' : 'Save'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('/campaigns')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
