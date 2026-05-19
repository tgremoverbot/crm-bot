import { http } from './client';
import type { User } from '../types';

export const userApi = {
  list: (limit = 50, offset = 0) =>
    http.get<User[]>(`/api/admin/users?limit=${limit}&offset=${offset}`),
};
