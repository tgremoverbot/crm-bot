import { http } from './client';
import type { Material, MaterialKind, ParseMode } from '../types';

export interface MaterialPayload {
  name: string;
  kind: MaterialKind;
  body?: string | null;
  file_id?: string | null;
  file_url?: string | null;
  link_url?: string | null;
  parse_mode?: ParseMode;
  disable_web_page_preview?: boolean;
}

export const materialApi = {
  list: () => http.get<Material[]>('/api/admin/materials'),
  get: (id: string) => http.get<Material>(`/api/admin/materials/${id}`),
  create: (data: MaterialPayload) =>
    http.post<Material>('/api/admin/materials', data),
  update: (id: string, data: Partial<MaterialPayload>) =>
    http.patch<Material>(`/api/admin/materials/${id}`, data),
  remove: (id: string) => http.delete(`/api/admin/materials/${id}`),
};
