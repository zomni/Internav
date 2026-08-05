import { create } from 'zustand';
import type { User, LoginResponse } from '../types';
import { api, setTokens, clearTokens } from '../services/api';

const USER_STORAGE_KEY = 'internav.auth.user';

function loadStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

function saveStoredUser(user: User | null) {
  try {
    if (user) localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // ignore storage errors
  }
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: loadStoredUser(),
  loading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const data: LoginResponse = await api.login(email, password);
      setTokens(data.access_token, data.refresh_token);
      saveStoredUser(data.user);
      set({ user: data.user, loading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      set({ loading: false, error: message });
      throw err;
    }
  },

  logout: () => {
    clearTokens();
    saveStoredUser(null);
    set({ user: null, error: null });
  },
}));
