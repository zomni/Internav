import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);

  return {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'Administrator',
    isOperator: user?.role === 'Administrator' || user?.role === 'Operator',
  };
}
