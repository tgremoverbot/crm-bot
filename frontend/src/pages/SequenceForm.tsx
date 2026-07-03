import PageHeader from '../components/PageHeader';
import FullPageLoading from '../components/FullPageLoading';
import LoadingState from '../components/LoadingState';
import ConfirmModal from '../components/ConfirmModal';
import { Plus, Trash2 } from 'lucide-react';
import { useSequenceForm } from '../hooks/useSequenceForm';

function formatDelay(minutes: number): string {
  if (minutes === 0) return 'Sends immediately';
  if (minutes < 60) return `Sends after ${minutes} min`;
  if (minutes < 1440) return `Sends after ${minutes / 60} hour${minutes / 60 === 1 ? '' : 's'}`;
  const days = minutes / 1440;
  return `Sends after ${days} day${days === 1 ? '' : 's'}`;
}

export default function SequenceForm() {
  const {
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
    isPending,
    isAddStepPending,
    handleSubmit,
    handleAddStep,
    handleDeleteStep,
    handleCancel,
  } = useSequenceForm();

  if (isEdit && isLoading) return <FullPageLoading />;

  // Normalise steps so create (local drafts) and edit (persisted rows) render identically.
  const displaySteps = isEdit
    ? (steps ?? []).map((s) => ({
        key: s.id,
        materialId: s.material_id,
        delayMinutes: s.delay_minutes,
        onRemove: () => setDeleteStepId(s.id),
      }))
    : draftSteps.map((s, i) => ({
        key: `draft-${i}`,
        materialId: s.materialId,
        delayMinutes: s.delayMinutes,
        onRemove: () => removeDraftStep(i),
      }));

  const materialName = (materialId: string) =>
    materials?.find((m) => m.id === materialId)?.name ?? materialId;

  return (
    <div className="p-6 max-w-2xl">
      <PageHeader title={isEdit ? 'Edit Auto-flow' : 'New Auto-flow'} />

      <form onSubmit={handleSubmit}>
        {/* Details */}
        <div className="card p-6 space-y-4 mb-6">
          <div>
            <label className="label">Name</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input-field" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label className="label">Starts when</label>
            <p className="text-sm text-[#8aab96]">Someone joins via an invite link with this auto-flow attached.</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="seq_active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="accent-brand-500"
            />
            <label htmlFor="seq_active" className="text-sm text-[#8aab96]">Active</label>
          </div>
        </div>

        {/* Message steps */}
        <div className="card p-6 mb-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-[#dff5ea]">Message steps</h2>
            <p className="text-xs text-[#4a7060] mt-1">
              Messages are sent in order after someone joins, using the delays you set.
              {isEdit && ' Step changes here are saved immediately.'}
            </p>
          </div>

          {isEdit && stepsLoading && <LoadingState />}

          {displaySteps.length > 0 ? (
            <div className="card overflow-hidden">
              {displaySteps.map((step, i) => (
                <div key={step.key} className="flex items-center gap-3 px-4 py-3 border-b border-[#1a2e24] last:border-0">
                  <span className="w-5 text-center text-xs font-mono text-[#4a7060]">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#dff5ea] truncate">{materialName(step.materialId)}</p>
                    <p className="text-xs text-[#4a7060]">{formatDelay(step.delayMinutes)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={step.onRemove}
                    className="p-1.5 rounded hover:bg-red-900/20 text-[#4a7060] hover:text-red-400 transition-colors shrink-0"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            !stepsLoading && (
              <p className="text-[#4a7060] text-sm">No steps yet. Add the first one below.</p>
            )
          )}

          {/* Add a step */}
          <div className="border-t border-[#1a2e24] pt-4">
            <p className="text-xs font-medium text-[#4a7060] uppercase tracking-wider mb-3">Add a message step</p>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="label">Message</label>
                <select
                  className="input-field"
                  value={newStepMaterialId}
                  onChange={(e) => setNewStepMaterialId(e.target.value)}
                >
                  <option value="">Select a message…</option>
                  {materials?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              <div className="w-36">
                <label className="label">Delay (min)</label>
                <input
                  type="number"
                  min={0}
                  className="input-field"
                  value={newStepDelay}
                  onChange={(e) => setNewStepDelay(Number(e.target.value))}
                />
              </div>
              <button
                type="button"
                className="btn-primary flex items-center gap-1.5 text-sm shrink-0"
                disabled={!newStepMaterialId || isAddStepPending}
                onClick={handleAddStep}
              >
                <Plus size={14} /> {isAddStepPending ? 'Adding…' : 'Add step'}
              </button>
            </div>
          </div>
        </div>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
        {saved && <p className="text-brand-400 text-sm mb-3">Saved.</p>}

        <div className="flex gap-3">
          <button type="submit" className="btn-primary" disabled={isPending}>
            {isEdit
              ? isPending ? 'Saving…' : 'Save changes'
              : isPending ? 'Creating…' : 'Create this flow'}
          </button>
          <button type="button" className="btn-secondary" onClick={handleCancel}>
            {isEdit ? 'Back to list' : 'Cancel'}
          </button>
        </div>
      </form>

      {deleteStepId && (
        <ConfirmModal
          title="Remove step?"
          message="This will remove the step from the auto-flow."
          confirmLabel="Remove"
          danger
          onConfirm={() => handleDeleteStep(deleteStepId)}
          onCancel={() => setDeleteStepId(null)}
        />
      )}
    </div>
  );
}
