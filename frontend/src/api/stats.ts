import { http } from './client';
import type { Stats } from '../types';

export const statsApi = {
  get: () => http.get<Stats>('/api/admin/stats'),
};
