import { http } from './client';
import type { MenuButton } from '../types';

export interface MenuButtonPayload {
  label: string;
  row: number;
  position: number;
  action_kind: 'text' | 'material';
  action_material_id?: string | null;
  action_text?: string | null;
  is_active: boolean;
}

export const menuButtonApi = {
  list: () => http.get<MenuButton[]>('/api/admin/menu-buttons'),
  create: (data: MenuButtonPayload) =>
    http.post<MenuButton>('/api/admin/menu-buttons', data),
  update: (id: string, data: Partial<MenuButtonPayload>) =>
    http.patch<MenuButton>(`/api/admin/menu-buttons/${id}`, data),
  remove: (id: string) => http.delete(`/api/admin/menu-buttons/${id}`),
};
