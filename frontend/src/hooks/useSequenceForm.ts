import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sequenceApi } from '../api/sequences';
import { materialApi } from '../api/materials';
import type { TriggerKind } from '../types';

// The trigger selector was removed; every auto-flow starts when someone joins
// via an invite link it is attached to. Kept as a constant for the create payload.
const DEFAULT_TRIGGER: TriggerKind = 'campaign_join';

export interface DraftStep {
  materialId: string;
  delayMinutes: number;
}

export function useSequenceForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = !!id;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  // Steps being assembled for a brand-new flow (create mode only). Persisted in
  // one shot when the user presses "Create this flow".
  const [draftSteps, setDraftSteps] = useState<DraftStep[]>([]);

  const [newStepMaterialId, setNewStepMaterialId] = useState('');
  const [newStepDelay, setNewStepDelay] = useState(0);
  const [deleteStepId, setDeleteStepId] = useState<string | null>(null);

  const { data: existing, isLoading } = useQuery({
    queryKey: ['sequence', id],
    queryFn: () => sequenceApi.get(id!),
    enabled: isEdit,
  });

  const { data: steps, isLoading: stepsLoading } = useQuery({
    queryKey: ['sequence-steps', id],
    queryFn: () => sequenceApi.listSteps(id!),
    enabled: isEdit,
  });

  const { data: materials } = useQuery({
    queryKey: ['materials'],
    queryFn: materialApi.list,
  });

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setDescription(existing.description ?? '');
      setIsActive(existing.is_active);
    }
  }, [existing]);

  // --- create: persist the sequence and all its draft steps in order ---
  const create = useMutation({
    mutationFn: async () => {
      const seq = await sequenceApi.create({
        name,
        description: description || null,
        trigger_kind: DEFAULT_TRIGGER,
        is_active: isActive,
      });
      try {
        for (let i = 0; i < draftSteps.length; i++) {
          await sequenceApi.addStep(seq.id, {
            position: i + 1,
            delay_minutes: draftSteps[i].delayMinutes,
            material_id: draftSteps[i].materialId,
          });
        }
      } catch {
        // The sequence exists now, so re-submitting would duplicate it. Hand
        // the user to its edit page (the source of truth) to finish the steps.
        qc.invalidateQueries({ queryKey: ['sequences'] });
        navigate(`/sequences/${seq.id}/edit`);
        throw new Error('partial');
      }
      return seq;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sequences'] });
      navigate('/sequences');
    },
    onError: (e) => {
      if ((e as Error).message === 'partial') {
        setError('Flow created, but some steps failed to save. Finish adding them here.');
      } else {
        setError('Failed to create auto-flow.');
      }
    },
  });

  // --- edit: save name/description/active ---
  const update = useMutation({
    mutationFn: () =>
      sequenceApi.update(id!, {
        name,
        description: description || null,
        is_active: isActive,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sequences'] });
      qc.invalidateQueries({ queryKey: ['sequence', id] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
    onError: () => setError('Failed to save changes.'),
  });

  // --- edit: add a step to an existing flow (persists immediately) ---
  const addStep = useMutation({
    mutationFn: () => {
      const nextPosition =
        (steps && steps.length ? Math.max(...steps.map((s) => s.position)) : 0) + 1;
      return sequenceApi.addStep(id!, {
        position: nextPosition,
        delay_minutes: newStepDelay,
        material_id: newStepMaterialId,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sequence-steps', id] });
      setNewStepMaterialId('');
      setNewStepDelay(0);
    },
    onError: () => setError('Failed to add step.'),
  });

  const deleteStep = useMutation({
    mutationFn: (stepId: string) => sequenceApi.deleteStep(stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sequence-steps', id] });
      setDeleteStepId(null);
    },
  });

  function handleAddStep() {
    setError('');
    if (!newStepMaterialId) return;
    if (isEdit) {
      addStep.mutate();
      return;
    }
    setDraftSteps((prev) => [
      ...prev,
      { materialId: newStepMaterialId, delayMinutes: newStepDelay },
    ]);
    setNewStepMaterialId('');
    setNewStepDelay(0);
  }

  function removeDraftStep(index: number) {
    setDraftSteps((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!name.trim()) {
      setError('Enter a name.');
      return;
    }
    if (isEdit) {
      update.mutate();
    } else {
      create.mutate();
    }
  }

  function handleDeleteStep(stepId: string) {
    deleteStep.mutate(stepId);
  }

  function handleCancel() {
    navigate('/sequences');
  }

  return {
    isEdit,
    isLoading,
    stepsLoading,
    name,
    setName,
    description,
    setDescription,
    isActive,
    setIsActive,
    error,
    saved,
    steps,
    draftSteps,
    removeDraftStep,
    newStepMaterialId,
    setNewStepMaterialId,
    newStepDelay,
    setNewStepDelay,
    deleteStepId,
    setDeleteStepId,
    materials,
    isPending: create.isPending || update.isPending,
    isAddStepPending: addStep.isPending,
    handleSubmit,
    handleAddStep,
    handleDeleteStep,
    handleCancel,
  };
}
