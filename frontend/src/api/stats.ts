import { http } from './client';
import type { Stats } from '../types';

export const statsApi = {
  get: (growthDays = 7) => http.get<Stats>(`/api/admin/stats?growth_days=${growthDays}`),
};
