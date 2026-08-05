import { useState, useCallback } from 'react';
import { api } from '../services/api';

export function useCrud<T extends { id: string }>(basePath: string) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const list = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<T[]>(basePath);
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [basePath]);

  const get = useCallback(
    async (id: string): Promise<T | null> => {
      try {
        return await api.get<T>(`${basePath}/${id}`);
      } catch {
        return null;
      }
    },
    [basePath],
  );

  const create = useCallback(
    async (body: Record<string, unknown>): Promise<T | null> => {
      try {
        const item = await api.post<T>(basePath, body);
        setItems((prev) => [...prev, item]);
        return item;
      } catch (err) {
        throw err;
      }
    },
    [basePath],
  );

  const update = useCallback(
    async (id: string, body: Record<string, unknown>): Promise<T | null> => {
      try {
        const item = await api.put<T>(`${basePath}/${id}`, body);
        setItems((prev) => prev.map((i) => (i.id === id ? item : i)));
        return item;
      } catch (err) {
        throw err;
      }
    },
    [basePath],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.delete<null>(`${basePath}/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
    },
    [basePath],
  );

  return { items, loading, error, list, get, create, update, remove };
}
