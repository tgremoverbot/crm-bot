import { http } from './client';
import type { Sequence, SequenceStep, TriggerKind } from '../types';

export interface SequencePayload {
  name: string;
  description?: string | null;
  trigger_kind?: TriggerKind;
  is_active?: boolean;
}

export interface StepPayload {
  position: number;
  delay_minutes: number;
  material_id: string;
}

export const sequenceApi = {
  list: () => http.get<Sequence[]>('/api/admin/sequences'),
  get: (id: string) => http.get<Sequence>(`/api/admin/sequences/${id}`),
  create: (data: SequencePayload) =>
    http.post<Sequence>('/api/admin/sequences', data),
  update: (id: string, data: Partial<SequencePayload>) =>
    http.patch<Sequence>(`/api/admin/sequences/${id}`, data),

  remove: (id: string) => http.delete(`/api/admin/sequences/${id}`),

  listSteps: (id: string) =>
    http.get<SequenceStep[]>(`/api/admin/sequences/${id}/steps`),
  addStep: (id: string, data: StepPayload) =>
    http.post<SequenceStep>(`/api/admin/sequences/${id}/steps`, data),
  updateStep: (stepId: string, data: Partial<StepPayload>) =>
    http.patch<SequenceStep>(`/api/admin/sequence-steps/${stepId}`, data),
  deleteStep: (stepId: string) =>
    http.delete(`/api/admin/sequence-steps/${stepId}`),
};
