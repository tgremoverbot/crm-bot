import { http } from './client';

export interface AppSettings {
  default_sequence_id: string | null;
}

export const settingsApi = {
  get: () => http.get<AppSettings>('/api/admin/settings'),
  update: (default_sequence_id: string | null) =>
    http.patch<AppSettings>('/api/admin/settings', { default_sequence_id }),
};
