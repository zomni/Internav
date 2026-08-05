export function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString();
}

export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ');
}
