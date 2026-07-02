import PageHeader from '../components/PageHeader';
import FullPageLoading from '../components/FullPageLoading';
import ErrorState from '../components/ErrorState';
import ConfirmModal from '../components/ConfirmModal';
import { Users, Send, Save } from 'lucide-react';
import { useBroadcastEdit } from '../hooks/useBroadcastEdit';

export default function BroadcastEdit() {
  const {
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
    isSavePending,
    isPreviewPending,
    isSendPending,
    handleSave,
    handlePreview,
    requestSend,
    confirmSend,
    cancelSend,
  } = useBroadcastEdit();

  if (isLoading) return <FullPageLoading />;
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
            disabled={isSavePending}
          >
            <Save size={14} /> {isSavePending ? 'Saving…' : 'Save draft'}
          </button>

          <button
            type="button"
            className="btn-secondary flex items-center gap-2 text-sm"
            onClick={handlePreview}
            disabled={isPreviewPending}
          >
            <Users size={14} /> {isPreviewPending ? 'Checking…' : 'Check recipients'}
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
            onClick={requestSend}
            disabled={isSendPending}
          >
            <Send size={14} /> {isSendPending ? 'Sending…' : scheduledAt ? 'Schedule send' : 'Send now'}
          </button>
        </div>
      </form>

      {confirmSendOpen && (
        <ConfirmModal
          title={scheduledAt ? 'Schedule this broadcast?' : 'Send this broadcast now?'}
          message={
            previewCount !== null
              ? `This will send "${name}" to ${previewCount.toLocaleString()} recipient${previewCount === 1 ? '' : 's'}. This cannot be undone.`
              : `This will send "${name}" to all matching recipients. Use "Check recipients" first if you want to know how many people that is. This cannot be undone.`
          }
          confirmLabel={scheduledAt ? 'Schedule' : 'Send now'}
          danger
          onConfirm={confirmSend}
          onCancel={cancelSend}
        />
      )}
    </div>
  );
}
