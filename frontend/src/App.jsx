import { useEffect, useState } from 'react';
import { api, getSession, setSession } from './api';

const TABS = ['Productos', 'Categorías', 'Ventas', 'Clientes', 'Historial'];

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
        <div className="logo-circle">
          <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
            <path d="M6 14h26l-5 16H11L6 14z" stroke="#23272a" strokeWidth="2.6" strokeLinejoin="round" fill="none"/>
            <circle cx="14" cy="38" r="3" fill="#23272a"/><circle cx="26" cy="38" r="3" fill="#23272a"/>
            <g fill="#15a092">
              <ellipse cx="33" cy="10" rx="3.4" ry="4.2"/>
              <circle cx="27" cy="7" r="2"/><circle cx="31.5" cy="4.6" r="2"/><circle cx="36" cy="5" r="2"/><circle cx="39" cy="8.4" r="2"/>
            </g>
          </svg>
        </div>
        <div>
          <h1><span className="ani">ANI</span><span className="mall">Mall</span></h1>
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
        <div className="logo-circle lg">
          <svg width="52" height="52" viewBox="0 0 48 48" fill="none">
            <path d="M6 14h26l-5 16H11L6 14z" stroke="#23272a" strokeWidth="2.6" strokeLinejoin="round" fill="none"/>
            <circle cx="14" cy="38" r="3" fill="#23272a"/><circle cx="26" cy="38" r="3" fill="#23272a"/>
            <g fill="#15a092">
              <ellipse cx="33" cy="10" rx="3.4" ry="4.2"/>
              <circle cx="27" cy="7" r="2"/><circle cx="31.5" cy="4.6" r="2"/><circle cx="36" cy="5" r="2"/><circle cx="39" cy="8.4" r="2"/>
            </g>
          </svg>
        </div>
        <h1><span className="ani">ANI</span><span className="mall">Mall</span></h1>
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
  const [stockProd, setStockProd] = useState(null);
  const [stockCant, setStockCant] = useState(1);
  const [stockErr, setStockErr] = useState('');

  const guardarStock = async () => {
    setStockErr('');
    const n = Number(stockCant);
    if (!Number.isInteger(n) || n <= 0) { setStockErr('Ingresá una cantidad entera mayor a 0.'); return; }
    try { await api.ingreso(stockProd.id, n); setStockProd(null); load(); }
    catch (e) { setStockErr(e.message); }
  };

  const openEdit = (p) => {
    setEditProd(p);
    setEditForm({
      nombre: p.nombre, marca: p.marca || '', descripcion: p.descripcion || '',
      unidad: p.unidad, precio_costo: p.precio_costo, precio_venta: p.precio_venta,
      stock_minimo: p.stock_minimo, imagen_url: p.imagen_url || '', sku: p.sku || '',
      activo: p.activo, categoria_ids: (p.categorias || []).map(c => c.id),
    });
  };
  const guardarEdit = async () => {
    try {
      const payload = { ...editForm, precio_costo: +editForm.precio_costo, precio_venta: +editForm.precio_venta, stock_minimo: +editForm.stock_minimo, sku: editForm.sku || null, imagen_url: editForm.imagen_url || null, categoria_ids: editForm.categoria_ids.map(Number) };
      await api.patchProd(editProd.id, payload); setEditProd(null); load();
    } catch (e) { alert(e.message); }
  };

  const loadCats = async () => setAllCats(await api.cats().catch(() => []));
  const load = async () => {
    setErr('');
    try { setItems(await api.prods({ search: search || undefined, categoria: cat || undefined, stock_bajo: bajo || undefined })); }
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
    <table><thead><tr><th>SKU</th><th>Nombre</th><th>Precio</th><th>Stock</th><th>Cats</th><th>Activo</th><th>Acciones</th></tr></thead>
      <tbody>{items.map(p => <tr key={p.id} className={p.stock_bajo ? 'bajo' : ''}>
        <td>{p.sku || '-'}</td><td>{p.nombre} ({p.marca || '-'})</td><td>${p.precio_venta}</td>
        <td>{p.stock} (mín {p.stock_minimo})</td><td>{(p.categorias || []).length ? (p.categorias || []).map(c => c.nombre).join(', ') : <span className="sin-cat">Sin categoría</span>}</td>
        <td>{p.activo ? 'sí' : 'no'}</td>
        <td>
          <button onClick={() => { setStockProd(p); setStockCant(1); setStockErr(''); }}>+stock</button>
          <button onClick={() => openEdit(p)}>editar</button>
          <button onClick={async () => { try { await api.patchProd(p.id, { activo: !p.activo }); load(); } catch (e) { alert(e.message); } }}>{p.activo ? 'desactivar' : 'activar'}</button>
          {isAdmin && <button onClick={async () => { if (confirm(`Eliminar "${p.nombre}"? Solo si no tiene ventas.`)) { try { await api.deleteProd(p.id); load(); } catch (e) { alert(e.message); } } }}>eliminar</button>}
        </td></tr>)}
      </tbody></table>
    <Modal open={!!stockProd} onClose={() => setStockProd(null)} title={stockProd ? `Ingresar stock · ${stockProd.nombre}` : 'Ingresar stock'}>
      <p className="muted">Stock actual: {stockProd?.stock}</p>
      <input type="number" min="1" step="1" value={stockCant} onChange={e => setStockCant(e.target.value)} placeholder="Cantidad" />
      {stockErr && <p className="err">{stockErr}</p>}
      <div className="modal-actions"><button className="ghost" onClick={() => setStockProd(null)}>Cancelar</button><button onClick={guardarStock}>Guardar</button></div>
    </Modal>
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo producto" wide>
      <div className="grid">
        <input placeholder="SKU" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} />
        <input placeholder="Nombre*" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} />
        <input placeholder="Marca" value={form.marca} onChange={e => setForm({ ...form, marca: e.target.value })} />
        <select value={form.unidad} onChange={e => setForm({ ...form, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select>
        <input type="number" placeholder="Costo" value={form.precio_costo} onChange={e => setForm({ ...form, precio_costo: e.target.value })} />
        <input type="number" placeholder="Venta*" value={form.precio_venta} onChange={e => setForm({ ...form, precio_venta: e.target.value })} />
        <input type="number" placeholder="Stock" value={form.stock} onChange={e => setForm({ ...form, stock: e.target.value })} />
        <input type="number" placeholder="Mín" value={form.stock_minimo} onChange={e => setForm({ ...form, stock_minimo: e.target.value })} />
        <input placeholder="imagen URL" value={form.imagen_url} onChange={e => setForm({ ...form, imagen_url: e.target.value })} />
        <input placeholder="Descripción" value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} />
      </div>
      <p>Categorías (opcional, puede quedar Sin categoría): {allCats.map(c => <label key={c.id}><input type="checkbox" checked={form.categoria_ids.includes(c.id)} onChange={e => setForm({ ...form, categoria_ids: e.target.checked ? [...form.categoria_ids, c.id] : form.categoria_ids.filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={crear}>Guardar</button></div>
    </Modal>
    <Modal open={!!editProd} onClose={() => setEditProd(null)} title={editProd ? `Editar · ${editProd.nombre}` : 'Editar'} wide>
      <div className="grid">
        <input placeholder="SKU" value={editForm.sku || ''} onChange={e => setEditForm({ ...editForm, sku: e.target.value })} />
        <input placeholder="Nombre*" value={editForm.nombre || ''} onChange={e => setEditForm({ ...editForm, nombre: e.target.value })} />
        <input placeholder="Marca" value={editForm.marca || ''} onChange={e => setEditForm({ ...editForm, marca: e.target.value })} />
        <select value={editForm.unidad || 'unidad'} onChange={e => setEditForm({ ...editForm, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select>
        <input type="number" placeholder="Costo" value={editForm.precio_costo ?? 0} onChange={e => setEditForm({ ...editForm, precio_costo: e.target.value })} />
        <input type="number" placeholder="Venta*" value={editForm.precio_venta ?? 0} onChange={e => setEditForm({ ...editForm, precio_venta: e.target.value })} />
        <input type="number" placeholder="Mín" value={editForm.stock_minimo ?? 10} onChange={e => setEditForm({ ...editForm, stock_minimo: e.target.value })} />
        <input placeholder="imagen URL" value={editForm.imagen_url || ''} onChange={e => setEditForm({ ...editForm, imagen_url: e.target.value })} />
        <input placeholder="Descripción" value={editForm.descripcion || ''} onChange={e => setEditForm({ ...editForm, descripcion: e.target.value })} />
        <label><input type="checkbox" checked={!!editForm.activo} onChange={e => setEditForm({ ...editForm, activo: e.target.checked })} /> activo</label>
      </div>
      <p>Categorías (vacío = Sin categoría): {allCats.map(c => <label key={c.id}><input type="checkbox" checked={(editForm.categoria_ids || []).includes(c.id)} onChange={e => setEditForm({ ...editForm, categoria_ids: e.target.checked ? [...(editForm.categoria_ids || []), c.id] : (editForm.categoria_ids || []).filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <div className="modal-actions"><button className="ghost" onClick={() => setEditProd(null)}>Cancelar</button><button onClick={guardarEdit}>Guardar cambios</button></div>
    </Modal>
  </section>;
}

/* ---------- Ventas ---------- */
function Ventas() {
  const [clientes, setClientes] = useState([]); const [prods, setProds] = useState([]); const [pedidos, setPedidos] = useState([]);
  const [err, setErr] = useState('');
  const [f, setF] = useState({ cliente_id: '', metodo_pago: 'efectivo', descuento_tipo: 'ningun', descuento_valor: 0 });
  const [lineas, setLineas] = useState([{ producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }]);
  const [open, setOpen] = useState(false);
  const load = async () => {
    try { setClientes(await api.clientes()); setProds(await api.prods()); setPedidos(await api.pedidos()); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { load(); }, []);
  const resetPedido = () => {
    setF({ cliente_id: '', metodo_pago: 'efectivo', descuento_tipo: 'ningun', descuento_valor: 0 });
    setLineas([{ producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }]);
  };
  const submit = async () => {
    if (!f.cliente_id) { alert('Elegí un cliente'); return; }
    if (lineas.some(l => !l.producto_id)) { alert('Hay líneas sin producto'); return; }
    try {
      const r = await api.createPedido({ cliente_id: +f.cliente_id, metodo_pago: f.metodo_pago, descuento_tipo: f.descuento_tipo, descuento_valor: +f.descuento_valor, detalles: lineas.map(l => ({ producto_id: +l.producto_id, cantidad: +l.cantidad, descuento_tipo: l.descuento_tipo, descuento_valor: +l.descuento_valor })) });
      alert(`Pedido ${r.id} total $${r.total}`); setOpen(false); resetPedido(); load();
    } catch (e) { alert(e.message); }
  };
  return <section>
    <div className="sec-head"><h2>Ventas / Pedidos</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo pedido</button></div>
    <Err e={err} />
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo pedido" wide>
      <div className="row">
        <select value={f.cliente_id} onChange={e => setF({ ...f, cliente_id: e.target.value })}><option value="">Cliente...</option>{clientes.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select>
        <select value={f.metodo_pago} onChange={e => setF({ ...f, metodo_pago: e.target.value })}><option>efectivo</option><option>tarjeta</option><option>transferencia</option><option>mercadopago</option></select>
        <select value={f.descuento_tipo} onChange={e => setF({ ...f, descuento_tipo: e.target.value })}><option value="ningun">sin dto</option><option value="porcentaje">% pedido</option><option value="monto_fijo">$ pedido</option></select>
        <input type="number" value={f.descuento_valor} onChange={e => setF({ ...f, descuento_valor: e.target.value })} />
      </div>
      {lineas.map((l, i) => <div className="row" key={i}>
        <select value={l.producto_id} onChange={e => setLineas(lineas.map((x, j) => j === i ? { ...x, producto_id: e.target.value } : x))}><option value="">Producto...</option>{prods.filter(p => p.activo).map(p => <option key={p.id} value={p.id}>{p.nombre} (stock {p.stock})</option>)}</select>
        <input type="number" min="1" value={l.cantidad} onChange={e => setLineas(lineas.map((x, j) => j === i ? { ...x, cantidad: e.target.value } : x))} />
        <select value={l.descuento_tipo} onChange={e => setLineas(lineas.map((x, j) => j === i ? { ...x, descuento_tipo: e.target.value } : x))}><option value="ningun">sin dto</option><option value="porcentaje">%</option><option value="monto_fijo">$</option></select>
        <input type="number" value={l.descuento_valor} onChange={e => setLineas(lineas.map((x, j) => j === i ? { ...x, descuento_valor: e.target.value } : x))} />
        <button onClick={() => setLineas(lineas.filter((_, j) => j !== i))}>-</button>
      </div>)}
      <div className="modal-actions">
        <button className="ghost" onClick={() => setLineas([...lineas, { producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }])}>+ línea</button>
        <span style={{ flex: 1 }} />
        <button className="ghost" onClick={() => setOpen(false)}>Cancelar</button>
        <button onClick={submit}>Guardar pedido</button>
      </div>
    </Modal>
    <h3>Pedidos</h3>
    <ul>{pedidos.map(p => <li key={p.id}>#{p.id} cli {p.cliente_id} ${p.total} {p.estado} {p.metodo_pago} {p.estado === 'pagado' && <button onClick={async () => { if (confirm(`Cancelar pedido #${p.id}? Se devuelve el stock.`)) { try { await api.cancelarPedido(p.id); load(); } catch (e) { alert(e.message); } } }}>cancelar</button>}</li>)}</ul>
  </section>;
}

/* ---------- Clientes ---------- */
function Clientes() {
  const { data, err, reload } = useLoad(api.clientes);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ nombre: '', email: '', telefono: '', dni: '', direccion: '' });
  const [selId, setSelId] = useState(null);
  const [selNombre, setSelNombre] = useState('');
  const [peds, setPeds] = useState([]);
  const [page, setPage] = useState(0);
  const [detId, setDetId] = useState(null); // pedido con detalle desplegado
  const PAGE = 5;

  const toggle = async (c) => {
    if (selId === c.id) { setSelId(null); setPeds([]); setDetId(null); return; } // esconder al segundo clic
    try {
      const list = await api.pedidosCliente(c.id);
      setSelId(c.id); setSelNombre(c.nombre); setPeds(list); setPage(0); setDetId(null);
    } catch (e) { alert(e.message); }
  };
  const dtoTxt = (t, v) => t === 'ningun' ? 'sin dto' : t === 'porcentaje' ? `${v}%` : `$${v}`;
  const fechaFmt = (f) => {
    if (!f) return '';
    const d = new Date(f);
    return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };
  const totalPages = Math.max(1, Math.ceil(peds.length / PAGE));
  const view = peds.slice(page * PAGE, page * PAGE + PAGE);

  return <section>
    <div className="sec-head"><h2>Clientes</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo</button></div>
    <Err e={err} />
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo cliente">
      <div className="grid">{['nombre', 'email', 'telefono', 'dni', 'direccion'].map(k => <input key={k} placeholder={k} value={f[k]} onChange={e => setF({ ...f, [k]: e.target.value })} />)}</div>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={async () => { try { await api.createCliente(f); setF({ nombre: '', email: '', telefono: '', dni: '', direccion: '' }); setOpen(false); reload(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
    </Modal>
    <ul>{(data || []).map(c => <li key={c.id}>
      {c.nombre} {c.email} DNI {c.dni}
      <button onClick={() => toggle(c)}>{selId === c.id ? 'ocultar' : 'ver pedidos'}</button>
      {selId === c.id && (
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
      )}
    </li>)}</ul>
  </section>;
}

/* ---------- Historial por día ---------- */
function Stock() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [dia, setDia] = useState(hoy);
  const [pedidos, setPedidos] = useState([]); const [movs, setMovs] = useState([]);
  const [rep, setRep] = useState(null); const [names, setNames] = useState({});
  const [err, setErr] = useState(''); const [loading, setLoading] = useState(false);

  const load = async (f) => {
    setLoading(true); setErr('');
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

  return <section>
    <div className="sec-head"><h2>Historial del día</h2><button className="fab" onClick={() => { setDia(hoy); load(hoy); }}>Hoy</button></div>
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
        <h3>Ventas del {dia}</h3>
        {pedidos.length === 0 ? <p className="muted">Sin movimientos este día.</p> :
          <ul>{pedidos.map(p => <li key={p.id}>#{p.id} · {p.estado} · ${p.total} · {p.metodo_pago}<br />
            <small>{(p.detalles || []).map(d => `${d.nombre_snapshot} x${d.cantidad}`).join(' · ')}</small></li>)}</ul>}
      </div>
      <div>
        <h3>Ingresos y egresos</h3>
        {movs.length === 0 ? <p className="muted">Sin movimientos este día.</p> :
          <ul>{movs.map(m => <li key={m.id}>
            <b className={m.tipo === 'INGRESO' ? 'in' : m.tipo === 'EGRESO_VENTA' ? 'out' : 'dev'}>
              {m.tipo === 'INGRESO' ? '+ingreso' : m.tipo === 'EGRESO_VENTA' ? '-venta' : '+devolución'}</b>
            {' '}{names[m.producto_id] || `prod ${m.producto_id}`} x{m.cantidad} <small>{fmt(m.fecha)} · {m.stock_anterior}→{m.stock_nuevo}{m.pedido_id ? ` · ped #${m.pedido_id}` : ''}</small>
          </li>)}</ul>}
      </div>
    </div>
  </section>;
}
