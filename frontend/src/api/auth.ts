import { http } from './client';
import type { AdminUser } from '../types';

export const authApi = {
  login: (email: string, password: string) =>
    http.post<{ access_token: string; token_type: string }>('/api/auth/login', {
      email,
      password,
    }),

  me: () => http.get<AdminUser>('/api/auth/me'),
};
