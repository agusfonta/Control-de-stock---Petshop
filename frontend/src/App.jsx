import { useEffect, useState } from 'react';
import { api, getSession, setSession } from './api';

const TABS = ['Productos', 'Ventas', 'Historial', 'Clientes', 'Categorías'];

// Estado de Ventas fuera del componente para persistir entre cambios de pestaña
const ventasState = {
  f: { cliente_id: '', metodo_pago: 'efectivo', descuento_tipo: 'ningun', descuento_valor: 0 },
  lineas: [{ producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }],
  clienteQuery: '',
};

export default function App() {
  const [tab, setTab] = useState('Productos');
  const [session, setSess] = useState(getSession);
  const [passOpen, setPassOpen] = useState(false);
  const [pc, setPc] = useState({ current: '', next: '' });
  const icons = { 'Productos': '🛒', 'Categorías': '🏷️', 'Ventas': '🧾', 'Clientes': '🐾', 'Historial': '📅', 'Usuarios': '👤' };
  useEffect(() => {
    const off = () => setSess(null);
    window.addEventListener('auth-expired', off);
    return () => window.removeEventListener('auth-expired', off);
  }, []);
  if (!session?.token) return <Login onOk={setSess} />;
  const tabs = session.rol === 'admin' ? [...TABS, 'Usuarios'] : TABS;
  return (
    <div className="wrap">
      <header className="brand">
        <img src="/logo.png" alt="AniMall" className="logo-img" />
        <div>
          <p>Alimentos · Snacks · Accesorios — panel de stock y ventas</p>
        </div>
        <span className="user-chip" title="Cambiar contraseña" onClick={() => { setPc({ current: '', next: '' }); setPassOpen(true); }} style={{ cursor: 'pointer' }}>🔒 {session.username} · {session.rol}</span>
        <button className="ghost" onClick={() => { setSession(null); setSess(null); }}>Salir</button>
      </header>
      <Modal open={passOpen} onClose={() => setPassOpen(false)} title="Cambiar contraseña">
        <input type="password" placeholder="Actual" value={pc.current} onChange={e => setPc({ ...pc, current: e.target.value })} />
        <input type="password" placeholder="Nueva (mín 6)" value={pc.next} onChange={e => setPc({ ...pc, next: e.target.value })} />
        <div className="modal-actions"><button className="ghost" onClick={() => setPassOpen(false)}>Cancelar</button><button onClick={async () => { try { await api.password(pc.current, pc.next); setPassOpen(false); alert('Contraseña actualizada'); } catch (e) { alert(e.message); } }}>Guardar</button></div>
      </Modal>
      <nav>{tabs.map(t => <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{icons[t]} {t}</button>)}</nav>
      <main>
        {tab === 'Productos' && <Productos isAdmin={session.rol === 'admin'} />}
        {tab === 'Categorías' && <Categorias isAdmin={session.rol === 'admin'} />}
        {tab === 'Ventas' && <Ventas />}
        {tab === 'Clientes' && <Clientes />}
        {tab === 'Historial' && <Stock />}
        {tab === 'Usuarios' && <Usuarios />}
      </main>
    </div>
  );
}

function Login({ onOk }) {
  const [u, setU] = useState(''); const [p, setP] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const go = async (e) => {
    e?.preventDefault(); setErr(''); setBusy(true);
    try {
      const r = await api.login(u, p);
      const s = { token: r.access_token, username: r.username, rol: r.rol };
      setSession(s); onOk(s);
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };
  return (
    <div className="wrap login-wrap">
      <form className="login-card" onSubmit={go}>
        <img src="/logo.png" alt="AniMall" className="logo-img lg" />
        <p className="muted">Ingresá para gestionar stock y ventas</p>
        <input placeholder="Usuario" value={u} onChange={e => setU(e.target.value)} autoFocus />
        <input placeholder="Contraseña" type="password" value={p} onChange={e => setP(e.target.value)} />
        {err && <p className="err">{err}</p>}
        <button disabled={busy}>{busy ? 'Ingresando...' : 'Ingresar'}</button>
        <p className="muted small">Primera vez: el seed crea admin / admin123</p>
      </form>
    </div>
  );
}

/* ---------- Usuarios (solo admin) ---------- */
function Usuarios() {
  const { data, err, loading, reload } = useLoad(api.users);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ username: '', password: '', rol: 'vendedor' });
  return <section>
    <div className="sec-head"><h2>Usuarios</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo</button></div>
    <Err e={err} />
    {loading ? 'Cargando...' : <ul>{(data || []).map(u => <li key={u.id}>{u.username} · {u.rol} · {u.activo ? 'activo' : 'inactivo'}</li>)}</ul>}
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo usuario">
      <input placeholder="Usuario (mín 3)" value={f.username} onChange={e => setF({ ...f, username: e.target.value })} />
      <input placeholder="Contraseña (mín 6)" type="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
      <select value={f.rol} onChange={e => setF({ ...f, rol: e.target.value })}><option value="vendedor">vendedor</option><option value="admin">admin</option></select>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={async () => { try { await api.register(f); setF({ username: '', password: '', rol: 'vendedor' }); setOpen(false); reload(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
    </Modal>
  </section>;
}

function useLoad(fn, deps = []) {
  const [data, setData] = useState(null); const [err, setErr] = useState(''); const [loading, setLoading] = useState(true);
  const reload = async () => {
    setLoading(true); setErr('');
    try { setData(await fn()); } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, deps);
  return { data, err, loading, reload };
}

function Err({ e }) { return e ? <p className="err">{e}</p> : null; }

function Field({ label, hint, className, children }) {
  return <label className={'field' + (className ? ' ' + className : '')}><span>{label}{hint && <small> — {hint}</small>}</span>{children}</label>;
}

function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null;
  return (
    <div className="overlay" onClick={onClose}>
      <div className={`modal ${wide ? 'wide' : ''}`} onClick={e => e.stopPropagation()}>
        <div className="modal-head"><h3>{title}</h3><button className="x" onClick={onClose}>✕</button></div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

/* ---------- Categorías ---------- */
function Categorias({ isAdmin }) {
  const { data, err, loading, reload } = useLoad(api.cats);
  const [open, setOpen] = useState(false);
  const [nombre, setNombre] = useState(''); const [desc, setDesc] = useState('');
  const crear = async () => {
    try { await api.createCat({ nombre, descripcion: desc || null }); setNombre(''); setDesc(''); setOpen(false); reload(); }
    catch (e) { alert(e.message); }
  };
  return <section>
    <div className="sec-head"><h2>Categorías</h2><button className="fab" onClick={() => setOpen(true)}>+ Nueva</button></div>
    <Err e={err} />
    {loading ? 'Cargando...' : <ul>{(data || []).map(c =>
      <li key={c.id} className="cat-li"><span>{c.nombre} — {c.descripcion || '-'}</span>{isAdmin && <button className="del" title="Eliminar categoría (los productos quedan Sin categoría)" onClick={async () => { if (confirm('Eliminar categoría? Los productos quedarán "Sin categoría" y podrás asignarles otra.')) { try { await api.deleteCat(c.id); reload(); } catch (e) { alert(e.message); } } }}>✕</button>}</li>)}
    </ul>}
    <Modal open={open} onClose={() => setOpen(false)} title="Nueva categoría">
      <input placeholder="Nombre" value={nombre} onChange={e => setNombre(e.target.value)} />
      <input placeholder="Descripción" value={desc} onChange={e => setDesc(e.target.value)} />
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={crear}>Guardar</button></div>
    </Modal>
  </section>;
}

/* ---------- Productos ---------- */
function Productos({ isAdmin }) {
  const [allCats, setAllCats] = useState([]);
  const [search, setSearch] = useState(''); const [cat, setCat] = useState(''); const [bajo, setBajo] = useState(false);
  const [items, setItems] = useState([]); const [err, setErr] = useState('');
  const [form, setForm] = useState({ sku: '', nombre: '', descripcion: '', marca: '', unidad: 'unidad', precio_costo: 0, precio_venta: 100, stock: 0, stock_minimo: 10, imagen_url: '', categoria_ids: [] });
  const [open, setOpen] = useState(false);
  const [editProd, setEditProd] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [stockCant, setStockCant] = useState(1);
  const [stockErr, setStockErr] = useState('');

  const guardarStock = async () => {
    setStockErr('');
    const n = Number(stockCant);
    if (!Number.isInteger(n) || n <= 0) { setStockErr('Ingresá una cantidad entera mayor a 0.'); return; }
    try { await api.ingreso(editProd.id, n); setEditProd({ ...editProd, stock: editProd.stock + n }); setStockCant(1); load(); }
    catch (e) { setStockErr(e.message); }
  };

  const openEdit = (p) => {
    setEditProd(p);
    setStockCant(1); setStockErr('');
    setEditForm({
      nombre: p.nombre, marca: p.marca || '', descripcion: p.descripcion || '',
      unidad: p.unidad, precio_costo: p.precio_costo, precio_venta: p.precio_venta,
      stock_minimo: p.stock_minimo, imagen_url: p.imagen_url || '', sku: p.sku || '',
      categoria_ids: (p.categorias || []).map(c => c.id),
    });
  };
  const guardarEdit = async () => {
    try {
      const payload = { ...editForm, precio_costo: +editForm.precio_costo, precio_venta: +editForm.precio_venta, stock_minimo: +editForm.stock_minimo, sku: editForm.sku || null, imagen_url: editForm.imagen_url || null, categoria_ids: editForm.categoria_ids.map(Number) };
      await api.patchProd(editProd.id, payload); setEditProd(null); load();
    } catch (e) { alert(e.message); }
  };
  const eliminarProd = async () => {
    if (!confirm(`Eliminar "${editProd.nombre}"? Solo es posible si no tiene ventas.`)) return;
    try { await api.deleteProd(editProd.id); setEditProd(null); load(); }
    catch (e) { alert(e.message); }
  };

  const loadCats = async () => setAllCats(await api.cats().catch(() => []));
  const load = async () => {
    setErr('');
    try { setItems(await api.prods({ search: search || undefined, categoria: cat || undefined, stock_bajo: bajo || undefined, solo_activos: true })); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { loadCats(); load(); }, []);

  const crear = async () => {
    try {
      const payload = { ...form, precio_costo: +form.precio_costo, precio_venta: +form.precio_venta, stock: +form.stock, stock_minimo: +form.stock_minimo, sku: form.sku || null, imagen_url: form.imagen_url || null, categoria_ids: form.categoria_ids.map(Number) };
      await api.createProd(payload); setOpen(false); load();
    } catch (e) { alert(e.message); }
  };
  return <section>
    <div className="sec-head"><h2>Productos</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo</button></div>
    <Err e={err} />
    <div className="row">
      <input placeholder="Buscar nombre/marca" value={search} onChange={e => setSearch(e.target.value)} />
      <select value={cat} onChange={e => setCat(e.target.value)}><option value="">Todas las categorías</option>{allCats.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select>
      <label><input type="checkbox" checked={bajo} onChange={e => setBajo(e.target.checked)} /> stock bajo</label>
      <button onClick={load}>Filtrar</button>
    </div>
    <table><thead><tr><th>SKU</th><th>Nombre</th><th>Precio</th><th>Stock</th><th>Cats</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody>{items.map(p => <tr key={p.id} className={p.stock_bajo ? 'bajo' : ''}>
        <td>{p.sku || '-'}</td><td>{p.nombre} ({p.marca || '-'})</td><td>${p.precio_venta}</td>
        <td>{p.stock} (mín {p.stock_minimo})</td><td>{(p.categorias || []).length ? (p.categorias || []).map(c => c.nombre).join(', ') : <span className="sin-cat">Sin categoría</span>}</td>
        <td>{p.stock === 0 ? <span className="badge out">Sin stock</span> : <span className="badge ok">Disponible</span>}</td>
        <td><button onClick={() => openEdit(p)}>editar</button></td></tr>)}
      </tbody></table>
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo producto" wide>
      <div className="grid">
        <Field label="SKU" hint="Código único del producto, opcional"><input placeholder="Ej: RC-MINI-3KG" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} /></Field>
        <Field label="Nombre*" hint="Nombre visible en listados y ventas"><input placeholder="Ej: Royal Canin Mini 3kg" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} /></Field>
        <Field label="Marca" hint="Marca o laboratorio"><input placeholder="Ej: Royal Canin" value={form.marca} onChange={e => setForm({ ...form, marca: e.target.value })} /></Field>
        <Field label="Unidad" hint="Cómo se vende y descuenta el stock"><select value={form.unidad} onChange={e => setForm({ ...form, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select></Field>
        <Field label="Costo" hint="Precio de compra, solo referencia interna"><input type="number" placeholder="0" value={form.precio_costo} onChange={e => setForm({ ...form, precio_costo: e.target.value })} /></Field>
        <Field label="Venta*" hint="Precio al público que se cobra"><input type="number" placeholder="100" value={form.precio_venta} onChange={e => setForm({ ...form, precio_venta: e.target.value })} /></Field>
        <Field label="Stock" hint="Unidades iniciales disponibles"><input type="number" placeholder="0" value={form.stock} onChange={e => setForm({ ...form, stock: e.target.value })} /></Field>
        <Field label="Mín" hint="Avisa stock bajo al llegar a este nivel"><input type="number" placeholder="10" value={form.stock_minimo} onChange={e => setForm({ ...form, stock_minimo: e.target.value })} /></Field>
        <Field label="Imagen URL" hint="Link http(s) de foto, opcional"><input placeholder="https://..." value={form.imagen_url} onChange={e => setForm({ ...form, imagen_url: e.target.value })} /></Field>
        <Field label="Descripción" hint="Detalle largo del producto"><input placeholder="Ej: Alimento para perro adulto" value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} /></Field>
      </div>
      <p>Categorías (opcional, puede quedar Sin categoría): {allCats.map(c => <label key={c.id}><input type="checkbox" checked={form.categoria_ids.includes(c.id)} onChange={e => setForm({ ...form, categoria_ids: e.target.checked ? [...form.categoria_ids, c.id] : form.categoria_ids.filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={crear}>Guardar</button></div>
    </Modal>
    <Modal open={!!editProd} onClose={() => setEditProd(null)} title={editProd ? `Editar · ${editProd.nombre}` : 'Editar'} wide>
      <div className="grid">
        <Field label="Codigo"><input placeholder="Ej: RC-MINI-3KG" value={editForm.sku || ''} onChange={e => setEditForm({ ...editForm, sku: e.target.value })} /></Field>
        <Field label="Nombre"><input placeholder="Ej: Royal Canin Mini 3kg" value={editForm.nombre || ''} onChange={e => setEditForm({ ...editForm, nombre: e.target.value })} /></Field>
        <Field label="Marca"><input placeholder="Ej: Royal Canin" value={editForm.marca || ''} onChange={e => setEditForm({ ...editForm, marca: e.target.value })} /></Field>
        <Field label="Unidad"><select value={editForm.unidad || 'unidad'} onChange={e => setEditForm({ ...editForm, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select></Field>
        <Field label="Costo" hint="Precio al costo"><input type="number" placeholder="0" value={editForm.precio_costo ?? 0} onChange={e => setEditForm({ ...editForm, precio_costo: e.target.value })} /></Field>
        <Field label="Venta" hint="Precio al público"><input type="number" placeholder="0" value={editForm.precio_venta ?? 0} onChange={e => setEditForm({ ...editForm, precio_venta: e.target.value })} /></Field>
        <Field label="Mín" hint="Avisa stock bajo al llegar a este minimo"><input type="number" placeholder="10" value={editForm.stock_minimo ?? 10} onChange={e => setEditForm({ ...editForm, stock_minimo: e.target.value })} /></Field>
        <Field label="Imagen URL" hint="Foto opcional"><input placeholder="https://..." value={editForm.imagen_url || ''} onChange={e => setEditForm({ ...editForm, imagen_url: e.target.value })} /></Field>
        <Field label="Descripción"><input placeholder="Ej: Alimento para perro adulto" value={editForm.descripcion || ''} onChange={e => setEditForm({ ...editForm, descripcion: e.target.value })} /></Field>
      </div>
      <p>Categorías: {allCats.map(c => <label key={c.id}><input type="checkbox" checked={(editForm.categoria_ids || []).includes(c.id)} onChange={e => setEditForm({ ...editForm, categoria_ids: e.target.checked ? [...(editForm.categoria_ids || []), c.id] : (editForm.categoria_ids || []).filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <div className="stock-box">
        <b>Stock actual: {editProd?.stock}</b>
        <div className="row">
          <input type="number" min="1" step="1" value={stockCant} onChange={e => setStockCant(e.target.value)} placeholder="Cantidad a ingresar" />
          <button onClick={guardarStock}>Ingresar stock</button>
        </div>
        {stockErr && <p className="err">{stockErr}</p>}
        <p className="muted small">Suma unidades al stock y lo registra en Historial como ingreso de mercadería.</p>
      </div>
      <div className="modal-actions">
        {isAdmin && <button className="danger" onClick={eliminarProd}>Eliminar</button>}
        <span style={{ flex: 1 }} />
        <button className="ghost" onClick={() => setEditProd(null)}>Cancelar</button>
        <button onClick={guardarEdit}>Guardar cambios</button>
      </div>
    </Modal>
  </section>;
}

/* ---------- ProdBuscador (Task 3) ---------- */
function ProdBuscador({ prods, value, onChange }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const norm = s => (s || '').toLowerCase();

  useEffect(() => {
    if (!value) { setQuery(''); return; }
    const p = prods.find(x => String(x.id) === String(value));
    if (p) setQuery(p.nombre);
  }, [value, prods]);

  const sugs = query.trim().length > 0
    ? prods.filter(p => p.activo && (norm(p.nombre).includes(norm(query)) || norm(p.marca || '').includes(norm(query))))
    : [];

  return (
    <div className="autocomplete-wrap">
      <input
        placeholder="Buscar producto..."
        value={query}
        autoComplete="off"
        onChange={e => { setQuery(e.target.value); onChange(''); setOpen(true); }}
        onFocus={() => { if (query.trim()) setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && sugs.length > 0 && (
        <ul className="sug-list">
          {sugs.map(p => (
            <li
              key={p.id}
              className={'sug-item' + (p.stock === 0 ? ' disabled' : '')}
              onMouseDown={p.stock > 0 ? () => { onChange(p.id); setQuery(p.nombre); setOpen(false); } : e => e.preventDefault()}
            >
              <span>{p.nombre}{p.marca ? ` · ${p.marca}` : ''}</span>
              {p.stock === 0
                ? <span className="badge out">Sin stock</span>
                : <span className="badge ok">stock: {p.stock}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------- Ventas ---------- */
function Ventas() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [clientes, setClientes] = useState([]);
  const [prods, setProds] = useState([]);
  const [pedidos, setPedidos] = useState([]);
  const [err, setErr] = useState('');

  // Persistir estado del formulario entre cambios de pestaña usando objeto externo
  const [f, setF] = useState(() => ventasState.f);
  const [lineas, setLineas] = useState(() => ventasState.lineas);
  const [clienteQuery, setClienteQuery] = useState(() => ventasState.clienteQuery);

  // Sincronizar con ventasState en cada cambio
  const setFP = v => { const val = typeof v === 'function' ? v(f) : v; ventasState.f = val; setF(val); };
  const setLineasP = v => { const val = typeof v === 'function' ? v(lineas) : v; ventasState.lineas = val; setLineas(val); };
  const setClienteQueryP = v => { ventasState.clienteQuery = v; setClienteQuery(v); };

  const [clienteOpen, setClienteOpen] = useState(false);

  // Modal nuevo cliente
  const [showNuevoCliente, setShowNuevoCliente] = useState(false);
  const [nuevoClienteForm, setNuevoClienteForm] = useState({ nombre: '', email: '', telefono: '', dni: '', direccion: '' });
  const [nuevoClienteErr, setNuevoClienteErr] = useState('');

  const norm = s => (s || '').toLowerCase();

  const load = async () => {
    try { setClientes(await api.clientes()); setProds(await api.prods()); setPedidos(await api.pedidos(hoy)); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { load(); }, []);

  const resetPedido = () => {
    const fInit = { cliente_id: '', metodo_pago: 'efectivo', descuento_tipo: 'ningun', descuento_valor: 0 };
    const lineasInit = [{ producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }];
    ventasState.f = fInit; setF(fInit);
    ventasState.lineas = lineasInit; setLineas(lineasInit);
    ventasState.clienteQuery = ''; setClienteQuery('');
    setShowNuevoCliente(false);
    setNuevoClienteErr('');
  };

  const submit = async () => {
    if (!f.cliente_id) { alert('Elegí un cliente'); return; }
    if (lineas.some(l => !l.producto_id)) { alert('Hay líneas sin producto'); return; }
    try {
      const r = await api.createPedido({ cliente_id: +f.cliente_id, metodo_pago: f.metodo_pago, descuento_tipo: f.descuento_tipo, descuento_valor: +f.descuento_valor, detalles: lineas.map(l => ({ producto_id: +l.producto_id, cantidad: +l.cantidad, descuento_tipo: l.descuento_tipo, descuento_valor: +l.descuento_valor })) });
      alert(`Venta #${r.id} registrada · total $${r.total}`); resetPedido(); load();
    } catch (e) { alert(e.message); }
  };

  const cliNombre = (id) => (clientes.find(c => c.id === id) || {}).nombre || `cli ${id}`;

  const cancelar = async (p) => {
    if (!confirm(`Cancelar venta #${p.id}? Se devuelve el stock.`)) return;
    try { await api.cancelarPedido(p.id); load(); } catch (e) { alert(e.message); }
  };

  const clienteSugs = clienteQuery.trim().length > 0
    ? clientes.filter(c => norm(c.nombre).includes(norm(clienteQuery.trim())))
    : [];

  const guardarNuevoCliente = async () => {
    setNuevoClienteErr('');
    try {
      const nuevo = await api.createCliente(nuevoClienteForm);
      const lista = await api.clientes();
      setClientes(lista);
      setFP(prev => ({ ...prev, cliente_id: nuevo.id }));
      setClienteQueryP(nuevo.nombre);
      setShowNuevoCliente(false);
      setClienteOpen(false);
      setNuevoClienteForm({ nombre: '', email: '', telefono: '', dni: '', direccion: '' });
    } catch (e) { setNuevoClienteErr(e.message); }
  };

  return <section>
    <div className="sec-head"><h2>Ventas · Hoy</h2></div>
    <Err e={err} />
    <div className="sale-box">
      <h3>Registrar venta</h3>
      <div className="row">
        {/* Buscador de clientes con dropdown */}
        <Field label="Cliente" hint="A quién se le vende">
          <div className="autocomplete-wrap">
            <input
              placeholder="Buscar cliente por nombre..."
              value={clienteQuery}
              autoComplete="off"
              onChange={e => { setClienteQueryP(e.target.value); setFP(prev => ({ ...prev, cliente_id: '' })); setClienteOpen(true); }}
              onFocus={() => { if (clienteQuery.trim()) setClienteOpen(true); }}
              onBlur={() => setTimeout(() => setClienteOpen(false), 150)}
            />
            {clienteOpen && clienteQuery.trim().length > 0 && (
              <ul className="sug-list">
                {clienteSugs.map(c => (
                  <li key={c.id} className="sug-item" onMouseDown={() => { setFP(prev => ({ ...prev, cliente_id: c.id })); setClienteQueryP(c.nombre); setClienteOpen(false); }}>
                    <span>{c.nombre}</span>
                    <span className="muted" style={{ fontSize: '12px' }}> — DNI {c.dni}{c.telefono ? ` · ${c.telefono}` : ''}</span>
                  </li>
                ))}
                {clienteSugs.length === 0 && (
                  <li className="sug-item sug-crear" onMouseDown={() => { setNuevoClienteForm(prev => ({ ...prev, nombre: clienteQuery.trim() })); setShowNuevoCliente(true); setClienteOpen(false); }}>
                    ➕ Crear &quot;{clienteQuery.trim()}&quot; como nuevo cliente
                  </li>
                )}
              </ul>
            )}
          </div>
        </Field>
        <Field label="Método de pago" hint="Cómo paga la venta"><select value={f.metodo_pago} onChange={e => setFP({ ...f, metodo_pago: e.target.value })}><option>efectivo</option><option>tarjeta</option><option>transferencia</option><option>mercadopago</option></select></Field>
        <Field label="Descuento del pedido" hint="Se aplica al total"><select value={f.descuento_tipo} onChange={e => setFP({ ...f, descuento_tipo: e.target.value })}><option value="ningun">sin dto</option><option value="porcentaje">% pedido</option><option value="monto_fijo">$ pedido</option></select></Field>
        <Field label="Valor del descuento" hint="Si no hay dto, 0"><input type="number" value={f.descuento_valor} onChange={e => setFP({ ...f, descuento_valor: e.target.value })} /></Field>
      </div>
      {lineas.map((l, i) => <div className="line" key={i}>
        <Field className="lp" label="Producto" hint="Con stock disponible">
          <ProdBuscador prods={prods} value={l.producto_id} onChange={id => setLineasP(lineas.map((x, j) => j === i ? { ...x, producto_id: id } : x))} />
        </Field>
        <Field className="lc" label="Cantidad" hint="Unidades"><input type="number" min="1" value={l.cantidad} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, cantidad: e.target.value } : x))} /></Field>
        <Field className="ld" label="Descuento" hint="De esta línea"><select value={l.descuento_tipo} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, descuento_tipo: e.target.value } : x))}><option value="ningun">sin dto</option><option value="porcentaje">%</option><option value="monto_fijo">$</option></select></Field>
        <Field className="lv" label="Valor" hint="Del dto línea"><input type="number" value={l.descuento_valor} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, descuento_valor: e.target.value } : x))} /></Field>
        {/* Solo mostrar el botón quitar si hay más de 1 línea */}
        {lineas.length > 1 && (
          <button className="ghost" title="Quitar línea" onClick={() => setLineasP(lineas.filter((_, j) => j !== i))}>-</button>
        )}
      </div>)}
      <div className="modal-actions">
        <button className="ghost" onClick={() => setLineasP([...lineas, { producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }])}>+ línea</button>
        <span style={{ flex: 1 }} />
        <button onClick={submit}>Guardar venta</button>
      </div>
    </div>
    <h3>Ventas de hoy</h3>
    {pedidos.length === 0 ? <p className="muted">Todavía no hay ventas hoy.</p> :
      <ul>{pedidos.map(p => <li key={p.id}>#{p.id} · {cliNombre(p.cliente_id)} · ${p.total} · {p.estado} · {p.metodo_pago}<br />
        <small>{(p.detalles || []).map(d => `${d.nombre_snapshot} x${d.cantidad}`).join(' · ')}</small>
        {p.estado === 'pagado' && <button onClick={() => cancelar(p)}>cancelar</button>}</li>)}</ul>}

    {/* Modal nuevo cliente — abre centrado y ocupa el ancho completo del modal */}
    <Modal open={showNuevoCliente} onClose={() => { setShowNuevoCliente(false); setNuevoClienteErr(''); }} title="Nuevo cliente" wide>
      <div className="grid">
        <Field label="Nombre*" hint="Nombre y apellido"><input placeholder="Martina López" value={nuevoClienteForm.nombre} onChange={e => setNuevoClienteForm(prev => ({ ...prev, nombre: e.target.value }))} /></Field>
        <Field label="Email*" hint="Email único del cliente"><input type="email" placeholder="martina@mail.com" value={nuevoClienteForm.email} onChange={e => setNuevoClienteForm(prev => ({ ...prev, email: e.target.value }))} /></Field>
        <Field label="Teléfono" hint="Opcional"><input placeholder="351-2345678" value={nuevoClienteForm.telefono} onChange={e => setNuevoClienteForm(prev => ({ ...prev, telefono: e.target.value }))} /></Field>
        <Field label="DNI*" hint="DNI único del cliente"><input placeholder="30123456" value={nuevoClienteForm.dni} onChange={e => setNuevoClienteForm(prev => ({ ...prev, dni: e.target.value }))} /></Field>
        <Field label="Dirección" hint="Opcional"><input placeholder="Av Colón 1234" value={nuevoClienteForm.direccion} onChange={e => setNuevoClienteForm(prev => ({ ...prev, direccion: e.target.value }))} /></Field>
      </div>
      {nuevoClienteErr && <p className="err">{nuevoClienteErr}</p>}
      <div className="modal-actions">
        <button className="ghost" onClick={() => { setShowNuevoCliente(false); setNuevoClienteErr(''); }}>Cancelar</button>
        <button onClick={guardarNuevoCliente}>Guardar cliente</button>
      </div>
    </Modal>
  </section>;
}

/* ---------- Clientes ---------- */
function Clientes() {
  const { data, err, reload } = useLoad(api.clientes);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ nombre: '', email: '', telefono: '', dni: '', direccion: '' });
  const [q, setQ] = useState('');
  const [selId, setSelId] = useState(null);
  const [peds, setPeds] = useState([]);
  const [page, setPage] = useState(0);
  const [detId, setDetId] = useState(null); // pedido con detalle desplegado
  const PAGE = 5;

  const toggle = async (c) => {
    if (selId === c.id) { setSelId(null); setPeds([]); setDetId(null); return; } // esconder al segundo clic
    try {
      const list = await api.pedidosCliente(c.id);
      setSelId(c.id); setPeds(list); setPage(0); setDetId(null);
    } catch (e) { alert(e.message); }
  };
  const dtoTxt = (t, v) => t === 'ningun' ? 'sin dto' : t === 'porcentaje' ? `${v}%` : `$${v}`;
  const fechaFmt = (f) => {
    if (!f) return '';
    const d = new Date(f);
    return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };
  const norm = (s) => (s || '').toLowerCase();
  const rows = (data || []).filter(c => {
    const t = norm(q.trim());
    if (!t) return true;
    return norm(c.nombre).includes(t) || norm(c.email).includes(t) || norm(c.dni).includes(t);
  });
  const totalPages = Math.max(1, Math.ceil(peds.length / PAGE));
  const view = peds.slice(page * PAGE, page * PAGE + PAGE);

  const pedsBlock = (
    <div className="peds">
      {peds.length === 0
        ? <p className="muted">Este cliente todavía no tiene pedidos.</p>
        : <>
          <ul>{view.map(p => <li key={p.id}>
            <b>📅 {fechaFmt(p.fecha)}</b> · pedido #{p.id} · {p.estado} · {p.metodo_pago}
            <button onClick={() => setDetId(detId === p.id ? null : p.id)}>{detId === p.id ? 'ocultar detalle' : 'ver detalle'}</button>
            {detId === p.id && (
              <div className="det">
                {(p.detalles || []).map(d => <div key={d.id} className="det-line">
                  <span>{d.nombre_snapshot} x{d.cantidad} @ ${d.precio_unitario}</span>
                  <span className="muted">dto: {dtoTxt(d.descuento_tipo, d.descuento_valor)} → ${d.subtotal_linea}</span>
                </div>)}
                <div className="det-total">
                  <span>Subtotal: ${p.subtotal} · Dto pedido: {dtoTxt(p.descuento_tipo, p.descuento_valor)}</span>
                  <b>Total: ${p.total} ARS</b>
                </div>
              </div>
            )}
          </li>)}</ul>
          {peds.length > PAGE && (
            <div className="pager">
              <button className="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>‹ Nuevos</button>
              <span>{page + 1} / {totalPages}</span>
              <button className="ghost" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Anteriores ›</button>
            </div>
          )}
        </>}
    </div>
  );

  return <section>
    <div className="sec-head"><h2>Clientes</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo</button></div>
    <Err e={err} />
    <div className="row">
      <input placeholder="Buscar nombre, email o DNI" value={q} onChange={e => setQ(e.target.value)} />
    </div>
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo cliente">
      <div className="grid">
        <Field label="Nombre" hint="Nombre y apellido del cliente"><input placeholder="Ej: Martina López" value={f.nombre} onChange={e => setF({ ...f, nombre: e.target.value })} /></Field>
        <Field label="Email" hint="Email único, identifica al cliente"><input placeholder="Ej: martina@mail.com" value={f.email} onChange={e => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Teléfono" hint="Teléfono de contacto, opcional"><input placeholder="Ej: 351-2345678" value={f.telefono} onChange={e => setF({ ...f, telefono: e.target.value })} /></Field>
        <Field label="DNI" hint="DNI único del cliente"><input placeholder="Ej: 30123456" value={f.dni} onChange={e => setF({ ...f, dni: e.target.value })} /></Field>
        <Field label="Dirección" hint="Dirección, opcional"><input placeholder="Ej: Av Colón 1234" value={f.direccion} onChange={e => setF({ ...f, direccion: e.target.value })} /></Field>
      </div>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={async () => { try { await api.createCliente(f); setF({ nombre: '', email: '', telefono: '', dni: '', direccion: '' }); setOpen(false); reload(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
    </Modal>
    <table><thead><tr><th>Nombre</th><th>Email</th><th>DNI</th><th>Teléfono</th><th>Dirección</th><th>Acciones</th></tr></thead>
      {rows.map(c => <tbody key={c.id}>
        <tr>
          <td>{c.nombre}</td><td>{c.email}</td><td>{c.dni}</td>
          <td>{c.telefono || '-'}</td><td>{c.direccion || '-'}</td>
          <td><button onClick={() => toggle(c)}>{selId === c.id ? 'ocultar' : 'ver pedidos'}</button></td>
        </tr>
        {selId === c.id && <tr><td colSpan={6}>{pedsBlock}</td></tr>}
      </tbody>)}
    </table>
    {rows.length === 0 && <p className="muted">Sin clientes para este filtro.</p>}
  </section>;
}

/* ---------- HistPager (Tasks 4+5) ---------- */
function HistPager({ total, page, setPage, size = 6 }) {
  if (total <= size) return null;
  const pages = Math.ceil(total / size);
  return (
    <div className="hist-pager">
      <button className="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>‹</button>
      {Array.from({ length: pages }, (_, i) => (
        <span key={i} className={'dot' + (i === page ? ' active' : '')} onClick={() => setPage(i)} />
      ))}
      <button className="ghost" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>›</button>
    </div>
  );
}

/* ---------- Historial por día ---------- */
function Stock() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [dia, setDia] = useState(hoy);
  const [pedidos, setPedidos] = useState([]); const [movs, setMovs] = useState([]);
  const [rep, setRep] = useState(null); const [names, setNames] = useState({});
  const [err, setErr] = useState(''); const [loading, setLoading] = useState(false);
  // Tasks 4+5: paginación independiente para cada sección
  const [pagPedidos, setPagPedidos] = useState(0);
  const [pagMovs, setPagMovs] = useState(0);
  const PAGE = 6;

  const load = async (f) => {
    setLoading(true); setErr('');
    setPagPedidos(0); setPagMovs(0);
    try {
      const [p, m, r, prods] = await Promise.all([
        api.pedidos(f), api.movs(null, f), api.reporte(f), api.prods().catch(() => []),
      ]);
      setPedidos(p); setMovs(m); setRep(r);
      const map = {}; prods.forEach(x => { map[x.id] = x.nombre; }); setNames(map);
    } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { load(dia); }, []);
  const mover = (d) => {
    const dt = new Date(dia + 'T12:00:00'); dt.setDate(dt.getDate() + d);
    const s = dt.toISOString().slice(0, 10); setDia(s); load(s);
  };
  const ingresos = movs.filter(m => m.tipo === 'INGRESO');
  const egresos = movs.filter(m => m.tipo === 'EGRESO_VENTA');
  const devol = movs.filter(m => m.tipo === 'DEVOLUCION_CANCEL');
  const fmt = (f) => (f || '').slice(11, 16);

  // Task 4: vista paginada de pedidos (máx 6)
  const pedidosView = pedidos.slice(pagPedidos * PAGE, pagPedidos * PAGE + PAGE);
  // Task 5: vista paginada de movimientos (máx 6)
  const movsView = movs.slice(pagMovs * PAGE, pagMovs * PAGE + PAGE);

  return <section>
    <div className="sec-head"><h2>{dia === hoy ? 'Historial · Hoy' : `Historial · ${dia}`}</h2>{dia === hoy
      ? <button className="fab" disabled>Hoy</button>
      : <button className="fab" onClick={() => { setDia(hoy); load(hoy); }}>‹ Volver a hoy</button>}</div>
    <Err e={err} />
    <div className="row day-picker">
      <button className="ghost" onClick={() => mover(-1)}>‹ Ayer</button>
      <input type="date" value={dia} max={hoy} onChange={e => { setDia(e.target.value); load(e.target.value); }} />
      <button className="ghost" onClick={() => mover(1)} disabled={dia >= hoy}>Mañana ›</button>
      {loading && <span> Cargando...</span>}
    </div>
    <div className="cards">
      <div className="card"><span>Ventas</span><b>${rep ? rep.total_ars : 0}</b><small>{rep ? rep.cantidad_pedidos : 0} pedidos pagados</small></div>
      <div className="card"><span>Unidades vendidas</span><b>{egresos.reduce((a, m) => a + m.cantidad, 0)}</b><small>{egresos.length} egresos</small></div>
      <div className="card"><span>Ingresos mercadería</span><b>+{ingresos.reduce((a, m) => a + m.cantidad, 0)}</b><small>{ingresos.length} ingresos</small></div>
      <div className="card"><span>Devoluciones</span><b>+{devol.reduce((a, m) => a + m.cantidad, 0)}</b><small>por cancelación</small></div>
    </div>
    <div className="cols">
      <div>
        <h3>{dia === hoy ? 'Ventas de hoy' : `Ventas del ${dia}`}</h3>
        {pedidos.length === 0 ? <p className="muted">Sin movimientos este día.</p> : <>
          <ul>{pedidosView.map(p => <li key={p.id}>#{p.id} · {p.estado} · ${p.total} · {p.metodo_pago}<br />
            <small>{(p.detalles || []).map(d => `${d.nombre_snapshot} x${d.cantidad}`).join(' · ')}</small></li>)}</ul>
          <HistPager total={pedidos.length} page={pagPedidos} setPage={setPagPedidos} />
        </>}
      </div>
      <div>
        <h3>Ingresos y egresos</h3>
        {movs.length === 0 ? <p className="muted">Sin movimientos este día.</p> : <>
          <ul>{movsView.map(m => <li key={m.id}>
            <b className={m.tipo === 'INGRESO' ? 'in' : m.tipo === 'EGRESO_VENTA' ? 'out' : 'dev'}>
              {m.tipo === 'INGRESO' ? '+ingreso' : m.tipo === 'EGRESO_VENTA' ? '-venta' : '+devolución'}</b>
            {' '}{names[m.producto_id] || `prod ${m.producto_id}`} x{m.cantidad} <small>{fmt(m.fecha)} · {m.stock_anterior}→{m.stock_nuevo}{m.pedido_id ? ` · ped #${m.pedido_id}` : ''}</small>
          </li>)}</ul>
          <HistPager total={movs.length} page={pagMovs} setPage={setPagMovs} />
        </>}
      </div>
    </div>
  </section>;
}
