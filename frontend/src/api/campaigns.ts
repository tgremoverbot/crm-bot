import { http } from './client';
import type { Campaign } from '../types';

export interface CampaignPayload {
  name: string;
  slug: string;
  description?: string | null;
  is_active?: boolean;
  default_sequence_id?: string | null;
}

export const campaignApi = {
  list: () => http.get<Campaign[]>('/api/admin/campaigns'),
  get: (id: string) => http.get<Campaign>(`/api/admin/campaigns/${id}`),
  create: (data: CampaignPayload) =>
    http.post<Campaign>('/api/admin/campaigns', data),
  update: (id: string, data: Partial<CampaignPayload>) =>
    http.patch<Campaign>(`/api/admin/campaigns/${id}`, data),
  remove: (id: string) => http.delete(`/api/admin/campaigns/${id}`),
};
