export const todayLocal = () => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

export const shiftLocalDay = (isoDate, days) => {
  const [y, m, d] = String(isoDate).split('-').map(Number);
  const value = new Date(y, m - 1, d, 12);
  value.setDate(value.getDate() + days);
  const yy = value.getFullYear();
  const mm = String(value.getMonth() + 1).padStart(2, '0');
  const dd = String(value.getDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
};

export const parseApiUtc = (value) => {
  if (!value) return null;
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(text)) {
    return new Date(`${text}Z`);
  }
  return new Date(text);
};

export const formatApiDate = (value) => {
  const d = parseApiUtc(value);
  if (!d || Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('es-AR');
};

export const formatApiTime = (value) => {
  const d = parseApiUtc(value);
  if (!d || Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
};

export const apiDateToLocalInput = (value) => {
  const d = parseApiUtc(value);
  if (!d || Number.isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};
