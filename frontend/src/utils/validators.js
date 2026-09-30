const isEmailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((v || '').trim());
const isPhoneOk = (v) => {
  const value = (v || '').trim();
  if (!value) return true;
  const normalized = value.replace(/[\s()-]/g, '');
  return /^\+?[0-9]{7,15}$/.test(normalized);
};
const errNombre = (v, min = 2) => {
  if (!(v || '').trim()) return 'Completá este campo';
  if ((v || '').trim().length < min) return `Mínimo ${min} caracteres`;
  return '';
};
const errMayor0 = (v, etiqueta = 'Debe ser mayor a 0') => {
  if (v === '' || v === null || v === undefined) return 'Completá este campo';
  const n = Number(v);
  if (!Number.isFinite(n)) return 'Ingresá un número válido';
  return n > 0 ? '' : etiqueta;
};
const errMayorIgual0 = (v) => {
  if (v === '' || v === null || v === undefined) return 'Completá este campo';
  const n = Number(v);
  if (!Number.isFinite(n)) return 'Ingresá un número válido';
  return n >= 0 ? '' : 'No puede ser negativo';
};
const errEnteroMin = (v, min = 1) => {
  if (v === '' || v === null || v === undefined) return 'Completá este campo';
  const n = Number(v);
  if (!Number.isInteger(n)) return 'Ingresá un número entero';
  return n >= min ? '' : `Mínimo ${min}`;
};
const errDtoValor = (tipo, valor) => {
  const n = Number(valor);
  if (!Number.isFinite(n)) return 'Ingresá un número válido';
  if (tipo === 'ningun') return n === 0 ? '' : 'Si es sin dto, valor 0';
  if (tipo === 'porcentaje') return (n >= 0 && n <= 100) ? '' : 'De 0 a 100';
  return n >= 0 ? '' : 'No puede ser negativo';
};

export { isEmailOk, isPhoneOk, errNombre, errMayor0, errMayorIgual0, errEnteroMin, errDtoValor };
