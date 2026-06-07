import { http } from './client';
import type { Broadcast } from '../types';

export interface BroadcastPayload {
  name: string;
  material_id: string;
  segment_id?: string | null;
  scheduled_at?: string | null;
}

export const broadcastApi = {
  list: () => http.get<Broadcast[]>('/api/admin/broadcasts'),
  get: (id: string) => http.get<Broadcast>(`/api/admin/broadcasts/${id}`),
  create: (data: BroadcastPayload) =>
    http.post<Broadcast>('/api/admin/broadcasts', data),
  preview: (segment_id?: string | null) =>
    http.post<{ recipient_count: number }>('/api/admin/broadcasts/preview', {
      segment_id: segment_id ?? null,
    }),
  update: (id: string, data: BroadcastPayload) =>
    http.patch<Broadcast>(`/api/admin/broadcasts/${id}`, data),
  send: (id: string, scheduled_at?: string | null) =>
    http.post<Broadcast>(`/api/admin/broadcasts/${id}/send`, {
      scheduled_at: scheduled_at ?? null,
    }),
  remove: (id: string) => http.delete(`/api/admin/broadcasts/${id}`),
};
