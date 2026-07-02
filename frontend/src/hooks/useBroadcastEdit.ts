import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { broadcastApi } from '../api/broadcasts';
import { materialApi } from '../api/materials';

export function useBroadcastEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [name, setName] = useState('');
  const [materialId, setMaterialId] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [confirmSendOpen, setConfirmSendOpen] = useState(false);

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

  function requestSend() {
    setError('');
    if (!name || !materialId) { setError('Name and message are required.'); return; }
    setConfirmSendOpen(true);
  }

  function confirmSend() {
    setConfirmSendOpen(false);
    send.mutate();
  }

  function cancelSend() {
    setConfirmSendOpen(false);
  }

  return {
    id,
    bc,
    isLoading,
    isError,
    materials,
    name,
    setName,
    materialId,
    setMaterialId,
    scheduledAt,
    setScheduledAt,
    previewCount,
    error,
    saved,
    confirmSendOpen,
    isSavePending: save.isPending,
    isPreviewPending: preview.isPending,
    isSendPending: send.isPending,
    handleSave,
    handlePreview: () => { setError(''); preview.mutate(); },
    requestSend,
    confirmSend,
    cancelSend,
  };
}
