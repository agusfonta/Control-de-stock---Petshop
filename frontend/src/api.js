const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const KEY = 'animall_auth';

export function getSession() {
  try { return JSON.parse(localStorage.getItem(KEY) || 'null'); }
  catch { return null; }
}
export function setSession(s) {
  if (s) localStorage.setItem(KEY, JSON.stringify(s));
  else localStorage.removeItem(KEY);
}

async function req(path, opts = {}) {
  const s = getSession();
  const r = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(s?.token ? { Authorization: `Bearer ${s.token}` } : {}),
      ...(opts.headers || {}),
    },
    ...opts,
  });
  if (r.status === 401) {
    setSession(null);
    window.dispatchEvent(new Event('auth-expired'));
    throw Object.assign(new Error('Sesión vencida, volvé a ingresar'), { status: 401 });
  }
  if (r.status === 403) {
    throw Object.assign(new Error('Sin permiso para esta acción (requiere admin)'), { status: 403 });
  }
  if (!r.ok) {
    let msg = `Error ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || JSON.stringify(j);
    } catch { msg = await r.text(); }
    throw Object.assign(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)), { status: r.status });
  }
  if (r.status === 204) return null;
  return r.json();
}

export const api = {
  login: (username, password) => req('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (d) => req('/auth/register', { method: 'POST', body: JSON.stringify(d) }),
  users: () => req('/auth/users'),
  password: (current, next) => req('/auth/password', { method: 'POST', body: JSON.stringify({ current, new: next }) }),
  cats: () => req('/categorias'),
  createCat: (d) => req('/categorias', { method: 'POST', body: JSON.stringify(d) }),
  deleteCat: (id) => req(`/categorias/${id}`, { method: 'DELETE' }),
  prods: (p = {}) => {
    const q = new URLSearchParams();
    if (p.categoria) q.set('categoria', p.categoria);
    if (p.search) q.set('search', p.search);
    if (p.stock_bajo) q.set('stock_bajo', 'true');
    if (p.solo_activos) q.set('solo_activos', 'true');
    if (p.proveedor) q.set('proveedor', p.proveedor);
    const s = q.toString();
    return req(`/productos${s ? `?${s}` : ''}`);
  },
  createProd: (d) => req('/productos', { method: 'POST', body: JSON.stringify(d) }),
  patchProd: (id, d) => req(`/productos/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteProd: (id) => req(`/productos/${id}`, { method: 'DELETE' }),
  ingreso: (id, cantidad) => req(`/productos/${id}/stock/ingreso`, { method: 'POST', body: JSON.stringify({ cantidad }) }),
  clientes: () => req('/clientes'),
  createCliente: (d) => req('/clientes', { method: 'POST', body: JSON.stringify(d) }),
  pedidosCliente: (id) => req(`/clientes/${id}/pedidos`),
  pedidos: (fecha) => req(`/pedidos${fecha ? `?fecha=${fecha}` : ''}`),
  createPedido: (d) => req('/pedidos', { method: 'POST', body: JSON.stringify(d) }),
  cancelarPedido: (id) => req(`/pedidos/${id}/cancelar`, { method: 'PATCH' }),
  movs: (producto_id, fecha) => {
    const q = new URLSearchParams();
    if (producto_id) q.set('producto_id', producto_id);
    if (fecha) q.set('fecha', fecha);
    const s = q.toString();
    return req(`/stock/movimientos${s ? `?${s}` : ''}`);
  },
  reporte: (fecha) => req(`/reportes/ventas${fecha ? `?fecha=${fecha}` : ''}`),
  proveedores: () => req('/proveedores'),
  createProv: (d) => req('/proveedores', { method: 'POST', body: JSON.stringify(d) }),
  saldosProv: () => req('/proveedores/saldos'),
  provMovs: (id) => req(`/proveedores/${id}/movimientos`),
  createProvMov: (id, d) => req(`/proveedores/${id}/movimientos`, { method: 'POST', body: JSON.stringify(d) }),
  compras: (p = {}) => {
    const q = new URLSearchParams();
    if (p.fecha) q.set('fecha', p.fecha);
    if (p.proveedor) q.set('proveedor', p.proveedor);
    if (p.pagada !== undefined && p.pagada !== '') q.set('pagada', p.pagada);
    if (p.entregada !== undefined && p.entregada !== '') q.set('entregada', p.entregada);
    const s = q.toString();
    return req(`/compras${s ? `?${s}` : ''}`);
  },
  createCompra: (d) => req('/compras', { method: 'POST', body: JSON.stringify(d) }),
  patchCompra: (id, d) => req(`/compras/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  entregarCompra: (id) => req(`/compras/${id}/entregar`, { method: 'PATCH' }),
  pagarCompra: (id, d) => req(`/compras/${id}/pagar`, { method: 'PATCH', body: JSON.stringify(d || {}) }),
  deleteCompra: (id) => req(`/compras/${id}`, { method: 'DELETE' }),
  deudasProv: () => req('/compras/deudas'),
  caja: (fecha) => req(`/caja${fecha ? `?fecha=${fecha}` : ''}`),
  createCajaMov: (d) => req('/caja', { method: 'POST', body: JSON.stringify(d) }),
  deleteCajaMov: (id) => req(`/caja/${id}`, { method: 'DELETE' }),
};
