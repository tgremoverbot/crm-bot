import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/auth';

export function useAuth() {
  const qc = useQueryClient();

  const login = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      localStorage.setItem('token', data.access_token);
    },
  });

  const logout = () => {
    localStorage.removeItem('token');
    qc.clear();
    window.location.hash = '#/login';
  };

  const isAuthenticated = () => !!localStorage.getItem('token');

  return { login, logout, isAuthenticated };
}
