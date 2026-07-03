import { useState } from 'react';
import PageHeader from '../components/PageHeader';
import FullPageLoading from '../components/FullPageLoading';
import type { MaterialKind, ParseMode } from '../types';
import { useMaterialForm } from '../hooks/useMaterialForm';

const KINDS: MaterialKind[] = [
  'text',
  'photo',
  'video',
  'voice',
  'audio',
  'video_note',
  'animation',
  'sticker',
  'document',
  'link',
];
const PARSE_MODES: ParseMode[] = ['HTML', 'MarkdownV2', 'none'];

const KIND_LABELS: Record<MaterialKind, string> = {
  text: 'Text message',
  photo: 'Photo',
  video: 'Video',
  voice: 'Voice note',
  audio: 'Audio',
  video_note: 'Video note (circle)',
  animation: 'GIF',
  sticker: 'Sticker',
  document: 'File',
  link: 'Link only',
};

export default function MaterialForm() {
  const {
    isEdit,
    isLoading,
    name,
    setName,
    kind,
    setKind,
    body,
    setBody,
    fileId,
    setFileId,
    fileUrl,
    setFileUrl,
    linkUrl,
    setLinkUrl,
    parseMode,
    setParseMode,
    disablePreview,
    setDisablePreview,
    error,
    isCaptured,
    isPending,
    handleSubmit,
    handleCancel,
  } = useMaterialForm();

  const [showFileId, setShowFileId] = useState(false);

  if (isEdit && isLoading) return <FullPageLoading />;

  const bodyLimit = kind === 'text' ? 4096 : 1024;
  const overLimit = body.length > bodyLimit;

  return (
    <div className="p-6">
      <PageHeader title={isEdit ? 'Edit Message' : 'New Message'} />

      <div className="flex flex-col md:flex-row gap-6">
        <div className="flex-1 min-w-0">
          <form onSubmit={handleSubmit} className="card p-6 space-y-4">
            {isCaptured && (
              <p className="text-xs text-brand-300 bg-brand-500/10 border border-brand-500/20 rounded-md px-3 py-2">
                This message was captured from Telegram (send /admin to the bot). It's always
                delivered exactly as originally sent — the fields below are read-only. To send
                different content, send a new message to the bot in /admin mode instead.
              </p>
            )}
            <div>
              <label className="label">Name</label>
              <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div>
              <label className="label">Message type</label>
              <select
                className="input-field"
                value={kind}
                onChange={(e) => setKind(e.target.value as MaterialKind)}
                disabled={isCaptured}
              >
                {KINDS.map((k) => <option key={k} value={k}>{KIND_LABELS[k]}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Message text</label>
              <textarea
                className="input-field font-mono text-sm"
                rows={5}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Message text…"
                disabled={isCaptured}
              />
              <p className={`text-xs mt-1 ${overLimit ? 'text-red-400' : 'text-[#4a7060]'}`}>
                {body.length} / {bodyLimit}
              </p>
            </div>
            {kind !== 'text' && !isCaptured && (
              <>
                <div>
                  <label className="label">File URL</label>
                  <input className="input-field" type="url" value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} placeholder="https://…" />
                </div>
                {!showFileId && (
                  <button
                    type="button"
                    onClick={() => setShowFileId(true)}
                    className="text-xs text-[#4a7060] hover:text-brand-400"
                  >
                    + Use existing Telegram file ID
                  </button>
                )}
                {showFileId && (
                  <div>
                    <label className="label">Telegram File ID</label>
                    <input className="input-field font-mono text-sm" value={fileId} onChange={(e) => setFileId(e.target.value)} placeholder="AgACAgIAAxkB…" />
                  </div>
                )}
              </>
            )}
            {!isCaptured && (
              <div>
                <label className="label">Link URL (optional)</label>
                <input className="input-field" type="url" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://…" />
              </div>
            )}

            {!isCaptured && (
              <details>
                <summary className="cursor-pointer text-xs text-[#4a7060] mt-2">Advanced options</summary>
                <div className="space-y-4 mt-3">
                  <div>
                    <label className="label">Text formatting</label>
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
                    <label htmlFor="disable_preview" className="text-sm text-[#8aab96]">Disable link preview</label>
                  </div>
                </div>
              </details>
            )}

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn-primary" disabled={isPending}>
                {isPending ? 'Saving…' : 'Save'}
              </button>
              <button type="button" className="btn-secondary" onClick={handleCancel}>
                Cancel
              </button>
            </div>
          </form>
        </div>

        <div>
          <div className="bg-[#0d1f17] rounded-xl p-4 border border-[#1a2e24] min-w-[260px] max-w-[300px]">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-brand-500/30 flex items-center justify-center text-brand-400 text-xs font-bold">B</div>
              <span className="text-sm font-medium text-[#dff5ea] ml-2">Your Bot</span>
            </div>

            <div className="mt-3 bg-[#1a3a28] rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-[#dff5ea] whitespace-pre-wrap break-words max-w-full">
              {kind === 'text' && (
                <span className={body ? '' : 'text-[#4a7060]'}>
                  {body || 'Your message will appear here…'}
                </span>
              )}

              {(kind === 'photo' || kind === 'video' || kind === 'animation') && (
                <>
                  <div className="bg-[#0a2018] rounded-lg h-32 flex items-center justify-center text-[#2a4030] text-xs mb-2">
                    {kind === 'photo' ? 'Photo preview' : kind === 'video' ? 'Video preview' : 'GIF preview'}
                  </div>
                  {body && <span>{body}</span>}
                </>
              )}

              {kind === 'document' && (
                <>
                  <div className="bg-[#0a2018] rounded-lg px-3 py-2 flex items-center gap-2 mb-2">
                    <span>📄</span>
                    <span className="text-xs text-[#8aab96] truncate">{name || 'file.pdf'}</span>
                  </div>
                  {body && <span>{body}</span>}
                </>
              )}

              {(kind === 'voice' || kind === 'audio') && (
                <>
                  <div className="bg-[#0a2018] rounded-lg px-3 py-2 flex items-center gap-2 mb-2">
                    <span>{kind === 'voice' ? '🎤' : '🎵'}</span>
                    <span className="text-xs text-[#8aab96]">{kind === 'voice' ? 'Voice note' : 'Audio'}</span>
                  </div>
                  {body && <span>{body}</span>}
                </>
              )}

              {kind === 'video_note' && (
                <div className="bg-[#0a2018] rounded-full h-32 w-32 mx-auto flex items-center justify-center text-[#2a4030] text-xs">
                  Video note
                </div>
              )}

              {kind === 'sticker' && (
                <div className="bg-[#0a2018] rounded-lg h-32 flex items-center justify-center text-2xl">
                  🖼️
                </div>
              )}

              {kind === 'link' && (
                <span className="text-brand-400 underline">{linkUrl || 'https://your-link.com'}</span>
              )}
            </div>

            <div className="text-xs text-[#2a4030] mt-2 text-right">12:00</div>
          </div>
        </div>
      </div>
    </div>
  );
}
