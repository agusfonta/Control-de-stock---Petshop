import { useEffect, useState } from 'react';
import { api, getSession, setSession } from './api';

const TABS = ['Principal', 'Stock', 'Clientes', 'Distribuidoras', 'Historial'];

// Estado de Ventas fuera del componente para persistir entre cambios de pestaña
const ventasState = {
  f: { cliente_id: '', metodo_pago: 'efectivo', descuento_tipo: 'ningun', descuento_valor: 0 },
  lineas: [{ producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }],
  clienteQuery: '',
};

export default function App() {
  const [tab, setTab] = useState('Principal');
  const [session, setSess] = useState(getSession);
  const [passOpen, setPassOpen] = useState(false);
  const [pc, setPc] = useState({ current: '', next: '' });
  const icons = { 'Principal': '🧾', 'Stock': '📦', 'Clientes': '🐾', 'Distribuidoras': '🚚', 'Historial': '📅' };
  useEffect(() => {
    const off = () => setSess(null);
    window.addEventListener('auth-expired', off);
    return () => window.removeEventListener('auth-expired', off);
  }, []);
  if (!session?.token) return <Login onOk={setSess} />;
  const tabs = TABS;
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
        {tab === 'Principal' && <Ventas />}
        {tab === 'Stock' && <Productos isAdmin={session.rol === 'admin'} />}
        {tab === 'Clientes' && <Clientes />}
        {tab === 'Distribuidoras' && <Proveedores />}
        {tab === 'Historial' && <Caja />}
      </main>
    </div>
  );
}

function Login({ onOk }) {
  const [u, setU] = useState(''); const [p, setP] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [tU, setTU] = useState(false); const [tP, setTP] = useState(false);
  const eU = tU && !u.trim() ? 'Ingresá tu usuario' : '';
  const eP = tP && !p ? 'Ingresá tu contraseña' : '';
  const go = async (e) => {
    e?.preventDefault(); setErr(''); setTU(true); setTP(true);
    if (!u.trim() || !p) return;
    setBusy(true);
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
        <input placeholder="Usuario" value={u} onChange={e => setU(e.target.value)} onBlur={() => setTU(true)} autoFocus className={eU ? 'invalid' : ''} />
        {eU && <small className="field-err">{eU}</small>}
        <input placeholder="Contraseña" type="password" value={p} onChange={e => setP(e.target.value)} onBlur={() => setTP(true)} className={eP ? 'invalid' : ''} />
        {eP && <small className="field-err">{eP}</small>}
        {err && <p className="err">{err}</p>}
        <button disabled={busy}>{busy ? 'Ingresando...' : 'Ingresar'}</button>
        <p className="muted small">Primera vez: el seed crea admin / admin123</p>
      </form>
    </div>
  );
}

/* ---------- Principal eliminado: Ventas va directo; Caja vive en Historial ---------- */

/* ---------- Distribuidoras: pedidos de compra (pedido -> entrega -> pago) ---------- */
const MEDIO_TXT = { efectivo: 'EF · efectivo', transferencia: 'TR · transferencia', mercadopago: 'MP · mercadopago', debito: 'DB · débito', credito: 'CD · crédito', tarjeta: 'Tarjeta' };
const MEDIOS_SEL = Object.entries(MEDIO_TXT).filter(([v]) => v !== 'tarjeta');

function Proveedores() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [provs, setProvs] = useState([]);
  const [deudas, setDeudas] = useState([]);
  const [prods, setProds] = useState([]);
  const [lista, setLista] = useState([]);
  const [err, setErr] = useState('');
  const [f, setF] = useState({ proveedor_id: '', fecha_pedido: hoy, nro: '', lineas: [{ producto_id: '', cantidad: 1, costo: '' }], pagado: false, medio: 'transferencia' });
  const [tried, setTried] = useState(false);
  const [open, setOpen] = useState(false);
  const [nf, setNf] = useState({ nombre: '', contacto: '', telefono: '', alias: '', dias_entrega: '' });
  const [edit, setEdit] = useState(null);
  const [ef, setEf] = useState({});

  const deudaDe = (id) => (deudas.find(d => d.id === id) || {}).deuda || 0;
  const provDe = (id) => provs.find(p => String(p.id) === String(id)) || {};
  const costoBase = (pid) => (prods.find(p => String(p.id) === String(pid)) || {}).precio_costo || 0;
  const lineaTotal = (l) => (+l.cantidad || 0) * (l.costo === '' || l.costo == null ? costoBase(l.producto_id) : +l.costo);
  const totalForm = (lineas) => lineas.reduce((a, l) => a + lineaTotal(l), 0);
  const fmt = (n) => '$' + (+(n || 0)).toLocaleString('es-AR', { minimumFractionDigits: 2 });

  const loadBase = async () => {
    try {
      const [p, d, pr] = await Promise.all([api.proveedores(), api.deudasProv(), api.prods().catch(() => [])]);
      setProvs(p); setDeudas(d); setProds(pr);
    } catch (e) { setErr(e.message); }
  };
  const load = async () => {
    setErr('');
    try { setLista(await api.compras({})); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { loadBase(); load(); }, []);
  const recargarTodo = () => { loadBase(); load(); };

  const setLinea = (i, patch) => setF({ ...f, lineas: f.lineas.map((l, j) => j === i ? { ...l, ...patch } : l) });

  const guardar = async () => {
    setTried(true);
    if (!f.proveedor_id || !f.nro.trim()) return;
    if (f.lineas.some(l => !l.producto_id || !(+l.cantidad >= 1))) return;
    if (f.pagado && !f.medio) return;
    try {
      await api.createCompra({
        proveedor_id: +f.proveedor_id, nro_boleta: f.nro.trim(), fecha_pedido: f.fecha_pedido,
        detalles: f.lineas.map(l => ({ producto_id: +l.producto_id, cantidad: +l.cantidad, ...(l.costo === '' ? {} : { costo_unitario: +l.costo }) })),
        pagado: f.pagado, medio_pago: f.pagado ? f.medio : null,
      });
      setF({ proveedor_id: '', fecha_pedido: hoy, nro: '', lineas: [{ producto_id: '', cantidad: 1, costo: '' }], pagado: false, medio: 'transferencia' });
      setTried(false); recargarTodo();
    } catch (e) { alert(e.message); }
  };

  const entregar = async (c) => {
    if (!confirm(`Marcar pedido #${c.id} (${c.nro_boleta}) como entregado? Entra el stock.`)) return;
    try { await api.entregarCompra(c.id); recargarTodo(); } catch (e) { alert(e.message); }
  };
  const pagar = async (c) => {
    if (!c.medio_pago) { abrirEdit(c); alert('Elegí el medio de pago y marcá pagado en Editar.'); return; }
    if (!confirm(`Marcar pedido #${c.id} como pagado (${fmt(c.monto)} por ${MEDIO_TXT[c.medio_pago]})? Sale de caja.`)) return;
    try { await api.pagarCompra(c.id, {}); recargarTodo(); } catch (e) { alert(e.message); }
  };
  const borrar = async (c) => {
    if (!confirm(`Borrar pedido #${c.id}? Solo si no está entregado ni pagado.`)) return;
    try { await api.deleteCompra(c.id); recargarTodo(); } catch (e) { alert(e.message); }
  };

  const abrirEdit = (c) => {
    setEdit(c);
    setEf({
      nro: c.nro_boleta, fecha: (c.fecha_pedido || '').slice(0, 10),
      medio: c.medio_pago || 'transferencia', pagado: c.pagado,
      lineas: (c.detalles || []).map(d => ({ producto_id: d.producto_id, cantidad: d.cantidad, costo: d.costo_unitario })),
    });
  };
  const guardarEdit = async () => {
    if (!ef.nro.trim()) { alert('N° de boleta requerido'); return; }
    if (!edit.fecha_entrega && ef.lineas.some(l => !l.producto_id || !(+l.cantidad >= 1))) { alert('Revisá las líneas'); return; }
    if (ef.pagado && !edit.pagado && !ef.medio) { alert('Elegí medio de pago'); return; }
    try {
      await api.patchCompra(edit.id, {
        nro_boleta: ef.nro.trim(), fecha_pedido: ef.fecha,
        medio_pago: ef.medio || null,
        ...(!edit.fecha_entrega ? { detalles: ef.lineas.map(l => ({ producto_id: +l.producto_id, cantidad: +l.cantidad, costo_unitario: +l.costo })) } : {}),
      });
      if (ef.pagado && !edit.pagado) await api.pagarCompra(edit.id, { medio_pago: ef.medio });
      setEdit(null); recargarTodo();
    } catch (e) { alert(e.message); }
  };

  const selProv = provDe(f.proveedor_id);
  return <section>
    <div className="sec-head"><h2>Distribuidoras · Pedidos</h2><button className="fab" onClick={() => setOpen(true)}>+ Nueva</button></div>
    <Err e={err} />
    <div className="sale-box">
      <h3>Registrar pedido</h3>
      <div className="row">
        <Field label="Distribuidora" error={tried && !f.proveedor_id ? 'Elegí una' : ''}>
          <select value={f.proveedor_id} onChange={e => setF({ ...f, proveedor_id: e.target.value })} className={tried && !f.proveedor_id ? 'invalid' : ''}>
            <option value="">Elegir…</option>{provs.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </Field>
        <Field label="Fecha del pedido"><input type="date" value={f.fecha_pedido} max={hoy} onChange={e => setF({ ...f, fecha_pedido: e.target.value })} /></Field>
        <Field label="N° Boleta" error={tried && !f.nro.trim() ? 'Completá' : ''}>
          <input placeholder="99001" value={f.nro} onChange={e => setF({ ...f, nro: e.target.value })} className={tried && !f.nro.trim() ? 'invalid' : ''} />
        </Field>
      </div>
      {selProv.id && <p className="muted small">📦 Entregas: <b>{selProv.dias_entrega || '—'}</b>{selProv.alias ? <> · Alias: <b>{selProv.alias}</b></> : null} · Debe: <b>{fmt(deudaDe(selProv.id))}</b></p>}
      {f.lineas.map((l, i) => (
        <div className="line" key={i}>
          <Field className="lp" label="Producto" error={tried && !l.producto_id ? 'Elegí uno' : ''}>
            <ProdBuscador prods={prods} value={l.producto_id} allowSinStock onChange={id => setLinea(i, { producto_id: id })} />
          </Field>
          <Field className="lc" label="Cantidad" error={tried && !(+l.cantidad >= 1) ? 'Mín 1' : ''}>
            <input type="number" min="1" value={l.cantidad} onChange={e => setLinea(i, { cantidad: e.target.value })} className={tried && !(+l.cantidad >= 1) ? 'invalid' : ''} />
          </Field>
          <Field className="lv" label="Costo unit." hint={`Lista $${costoBase(l.producto_id)}`}>
            <input type="number" min="0" placeholder={String(costoBase(l.producto_id) || 0)} value={l.costo} onChange={e => setLinea(i, { costo: e.target.value })} />
          </Field>
          {f.lineas.length > 1 && <button className="ghost" title="Quitar línea" onClick={() => setF({ ...f, lineas: f.lineas.filter((_, j) => j !== i) })}>-</button>}
        </div>))}
      <div className="modal-actions">
        <button className="ghost" onClick={() => setF({ ...f, lineas: [...f.lineas, { producto_id: '', cantidad: 1, costo: '' }] })}>Agregar producto</button>
        <span style={{ flex: 1 }} />
        <label><input type="checkbox" checked={f.pagado} onChange={e => setF({ ...f, pagado: e.target.checked })} /> Pagado</label>
        {f.pagado && <select value={f.medio} onChange={e => setF({ ...f, medio: e.target.value })}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>}
        <b>Total: {fmt(totalForm(f.lineas))}</b>
        <button onClick={guardar}>Guardar pedido</button>
      </div>
    </div>
    <h3>Pedidos {lista.length > 0 && <span className="muted">· {lista.length}</span>}</h3>
    {lista.length === 0 ? <p className="muted">Sin pedidos todavía. Registrá el primero arriba.</p> :
      <ul className="peds-list">{lista.map(c => {
        const dets = c.detalles || [];
        const fechaPed = (c.fecha_pedido || '').slice(0, 10);
        return <li key={c.id} className="ped-card">
          <div className="ped-head">
            <b>#{c.id} · {c.proveedor_nombre}</b>
            <b className="in">{fmt(c.monto)}</b>
          </div>
          <div className="muted small ped-meta">Boleta {c.nro_boleta} · Pedido {fechaPed} · {dets.length} producto{dets.length === 1 ? '' : 's'}</div>
          {dets.length > 0 && <div className="det">
            {dets.map((d, i) => <div className="det-line" key={i}>
              <span>{d.producto_nombre || `prod ${d.producto_id}`} ×{d.cantidad}</span>
              <span>{fmt(d.subtotal)}</span>
            </div>)}
          </div>}
          <div className="ped-foot">
            <span className="ped-badges">
              {c.fecha_entrega
                ? <span className="badge ok">Entregada {(c.fecha_entrega || '').slice(0, 10)}</span>
                : <span className="badge out">Sin entregar</span>}{' '}
              {c.pagado
                ? <span className="badge ok">Pagada · {MEDIO_TXT[c.medio_pago] || c.medio_pago}</span>
                : <span className="badge out">Pendiente de pago</span>}
            </span>
            <span className="ped-actions">
              {!c.fecha_entrega && <button onClick={() => entregar(c)}>marcar entregado</button>}
              {!c.pagado && <button onClick={() => pagar(c)}>marcar pagado</button>}
              <button onClick={() => abrirEdit(c)}>editar</button>
              {!c.fecha_entrega && !c.pagado && <button onClick={() => borrar(c)}>borrar</button>}
            </span>
          </div>
        </li>; })}</ul>}
    <Modal open={!!edit} onClose={() => setEdit(null)} title={edit ? `Pedido #${edit.id} · ${edit.proveedor_nombre}` : 'Editar'} wide>
      <div className="grid">
        <Field label="N° Boleta"><input value={ef.nro || ''} onChange={e => setEf({ ...ef, nro: e.target.value })} /></Field>
        <Field label="Fecha del pedido"><input type="date" value={ef.fecha || ''} onChange={e => setEf({ ...ef, fecha: e.target.value })} /></Field>
        <Field label="Medio de pago"><select value={ef.medio || 'transferencia'} onChange={e => setEf({ ...ef, medio: e.target.value })}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></Field>
        <Field label="Entrega"><input value={edit?.fecha_entrega ? edit.fecha_entrega.slice(0, 10) : 'Sin entregar'} disabled /></Field>
      </div>
      <label><input type="checkbox" checked={!!ef.pagado} disabled={!!edit?.pagado} onChange={e => setEf({ ...ef, pagado: e.target.checked })} /> Pagado{edit?.pagado ? ' (no se puede desmarcar)' : ''}</label>
      {!edit?.fecha_entrega && <>
        <h3>Líneas (editable hasta entregar)</h3>
        {(ef.lineas || []).map((l, i) => (
          <div className="line" key={i}>
            <Field className="lp" label="Producto"><ProdBuscador prods={prods} value={l.producto_id} allowSinStock onChange={id => setEf({ ...ef, lineas: ef.lineas.map((x, j) => j === i ? { ...x, producto_id: id } : x) })} /></Field>
            <Field className="lc" label="Cantidad"><input type="number" min="1" value={l.cantidad} onChange={e => setEf({ ...ef, lineas: ef.lineas.map((x, j) => j === i ? { ...x, cantidad: e.target.value } : x) })} /></Field>
            <Field className="lv" label="Costo unit."><input type="number" min="0" value={l.costo} onChange={e => setEf({ ...ef, lineas: ef.lineas.map((x, j) => j === i ? { ...x, costo: e.target.value } : x) })} /></Field>
            {ef.lineas.length > 1 && <button className="ghost" onClick={() => setEf({ ...ef, lineas: ef.lineas.filter((_, j) => j !== i) })}>-</button>}
          </div>))}
        <button className="ghost" onClick={() => setEf({ ...ef, lineas: [...ef.lineas, { producto_id: '', cantidad: 1, costo: '' }] })}>Agregar producto</button>
      </>}
      <div className="modal-actions"><button className="ghost" onClick={() => setEdit(null)}>Cancelar</button><button onClick={guardarEdit}>Guardar cambios</button></div>
    </Modal>
    <Modal open={open} onClose={() => setOpen(false)} title="Nueva distribuidora">
      <Field label="Nombre*"><input placeholder="Distri Demo" value={nf.nombre} onChange={e => setNf({ ...nf, nombre: e.target.value })} /></Field>
      <Field label="Alias" hint="Alias MP para pagarle"><input placeholder="demo.mp" value={nf.alias} onChange={e => setNf({ ...nf, alias: e.target.value })} /></Field>
      <Field label="Entregas" hint="Ej: todos los días"><input placeholder="lun/mie/vie" value={nf.dias_entrega} onChange={e => setNf({ ...nf, dias_entrega: e.target.value })} /></Field>
      <Field label="Contacto"><input placeholder="ventas@demo.com" value={nf.contacto} onChange={e => setNf({ ...nf, contacto: e.target.value })} /></Field>
      <Field label="Teléfono"><input placeholder="000-000" value={nf.telefono} onChange={e => setNf({ ...nf, telefono: e.target.value })} /></Field>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={async () => { if (!nf.nombre.trim()) { alert('Nombre requerido'); return; } try { await api.createProv({ ...nf, nombre: nf.nombre.trim(), contacto: nf.contacto || null, telefono: nf.telefono || null, alias: nf.alias || null, dias_entrega: nf.dias_entrega || null }); setNf({ nombre: '', contacto: '', telefono: '', alias: '', dias_entrega: '' }); setOpen(false); loadBase(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
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

function Field({ label, hint, error, className, children }) {
  return <label className={'field' + (className ? ' ' + className : '')}><span>{label}{hint && <small> — {hint}</small>}</span>{children}{error && <small className="field-err">{error}</small>}</label>;
}

/* Validadores inline compartidos: devuelven '' si ok o el mensaje a mostrar debajo */
const isEmailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((v || '').trim());
const errNombre = (v, min = 2) => {
  if (!(v || '').trim()) return 'Completá este campo';
  if ((v || '').trim().length < min) return `Mínimo ${min} caracteres`;
  return '';
};
const errUrl = (v) => {
  if (!v) return '';
  const s = String(v).trim();
  if (!s) return '';
  return (s.startsWith('http://') || s.startsWith('https://')) ? '' : 'Debe empezar con http(s)://';
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

/* ---------- Categorías: crear desde el filtro de Stock; eliminar solo por API ---------- */

/* ---------- Productos ---------- */
function Productos({ isAdmin }) {
  const [allCats, setAllCats] = useState([]);
  const [allProvs, setAllProvs] = useState([]);
  const [search, setSearch] = useState(''); const [cat, setCat] = useState(''); const [prov, setProv] = useState(''); const [bajo, setBajo] = useState(false);
  const [items, setItems] = useState([]); const [err, setErr] = useState('');
  const [catOpen, setCatOpen] = useState(false);
  const [catNombre, setCatNombre] = useState(''); const [catDesc, setCatDesc] = useState('');
  const [form, setForm] = useState({ sku: '', nombre: '', descripcion: '', marca: '', unidad: 'unidad', precio_costo: 0, precio_venta: 100, stock_minimo: 10, categoria_ids: [], proveedor_id: '', proveedor_ids_alt: [] });
  const [open, setOpen] = useState(false);
  const [editProd, setEditProd] = useState(null);
  const [editForm, setEditForm] = useState({});
  const precioEfForm = Number(form.precio_venta) > 0 ? (Number(form.precio_venta) * 0.9).toFixed(2) : '—';
  const precioEfEdit = Number(editForm.precio_venta) > 0 ? (Number(editForm.precio_venta) * 0.9).toFixed(2) : '—';

  const openEdit = (p) => {
    setEditProd(p);
    setEditForm({
      nombre: p.nombre, marca: p.marca || '', descripcion: p.descripcion || '',
      unidad: p.unidad, precio_costo: p.precio_costo, precio_venta: p.precio_venta,
      stock_minimo: p.stock_minimo, sku: p.sku || '',
      categoria_ids: (p.categorias || []).map(c => c.id),
      proveedor_id: p.proveedor_id || '',
      proveedor_ids_alt: p.proveedor_ids_alt || [],
    });
  };
  const guardarEdit = async () => {
    const hayErr = errNombre(editForm.nombre || '', 2) || errMayor0(editForm.precio_venta, 'Debe ser mayor a 0') || errMayorIgual0(editForm.precio_costo) || errEnteroMin(editForm.stock_minimo, 0);
    if (hayErr) { alert(`Corregí lo marcado en rojo: ${hayErr}`); return; }
    try {
      const payload = { nombre: editForm.nombre, marca: editForm.marca || null, descripcion: editForm.descripcion || null, unidad: editForm.unidad, precio_costo: +editForm.precio_costo, precio_venta: +editForm.precio_venta, stock_minimo: +editForm.stock_minimo, sku: editForm.sku || null, categoria_ids: (editForm.categoria_ids || []).map(Number), proveedor_id: editForm.proveedor_id ? +editForm.proveedor_id : null, proveedor_ids_alt: (editForm.proveedor_ids_alt || []).map(Number) };
      await api.patchProd(editProd.id, payload); setEditProd(null); load();
    } catch (e) { alert(e.message); }
  };
  const eliminarProd = async () => {
    if (!confirm(`Eliminar "${editProd.nombre}"? Solo es posible si no tiene ventas.`)) return;
    try { await api.deleteProd(editProd.id); setEditProd(null); load(); }
    catch (e) { alert(e.message); }
  };

  const loadCats = async () => setAllCats(await api.cats().catch(() => []));
  const loadProvs = async () => setAllProvs(await api.proveedores().catch(() => []));
  const load = async () => {
    setErr('');
    try { setItems(await api.prods({ search: search || undefined, categoria: cat || undefined, proveedor: prov || undefined, stock_bajo: bajo || undefined, solo_activos: true })); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { loadCats(); loadProvs(); }, []);
  // Filtro automático (con debounce para el buscador)
  useEffect(() => {
    const t = setTimeout(async () => {
      setErr('');
      try { setItems(await api.prods({ search: search || undefined, categoria: cat || undefined, proveedor: prov || undefined, stock_bajo: bajo || undefined, solo_activos: true })); }
      catch (e) { setErr(e.message); }
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, cat, prov, bajo]);

  const crear = async () => {
    const hayErr = errNombre(form.nombre, 2) || errMayor0(form.precio_venta, 'Debe ser mayor a 0') || errMayorIgual0(form.precio_costo) || errEnteroMin(form.stock_minimo, 0);
    if (hayErr) { alert(`Corregí lo marcado en rojo: ${hayErr}`); return; }
    try {
      const payload = { ...form, precio_costo: +form.precio_costo, precio_venta: +form.precio_venta, stock: 0, stock_minimo: +form.stock_minimo, sku: form.sku || null, imagen_url: null, categoria_ids: form.categoria_ids.map(Number), proveedor_id: form.proveedor_id ? +form.proveedor_id : null, proveedor_ids_alt: (form.proveedor_ids_alt || []).map(Number) };
      await api.createProd(payload); setOpen(false); load();
    } catch (e) { alert(e.message); }
  };
  return <section>
    <div className="sec-head"><h2>Stock</h2><button className="fab" onClick={() => setOpen(true)}>+ Nuevo</button></div>
    <Err e={err} />
    <div className="row">
      <input placeholder="Buscar nombre/marca" value={search} onChange={e => setSearch(e.target.value)} />
      <select value={cat} onChange={e => { if (e.target.value === '__nueva__') { setCatNombre(''); setCatDesc(''); setCatOpen(true); } else setCat(e.target.value); }}><option value="">Todas las categorías</option>{allCats.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}<option value="__nueva__">＋ Crear nueva…</option></select>
      <select value={prov} onChange={e => setProv(e.target.value)}><option value="">Todas las distribuidoras</option>{allProvs.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select>
      <label><input type="checkbox" checked={bajo} onChange={e => setBajo(e.target.checked)} /> stock bajo</label>
    </div>
    <div className="tbl-wrap"><table><thead><tr><th>SKU</th><th>Nombre</th><th>Precio</th><th>Stock</th><th>Cats</th><th>Distribuidora</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody>{items.map(p => <tr key={p.id} className={p.stock_bajo ? 'bajo' : ''}>
        <td>{p.sku || '-'}</td><td>{p.nombre} ({p.marca || '-'})</td><td>${p.precio_venta}</td>
        <td>{p.stock} (mín {p.stock_minimo})</td><td>{(p.categorias || []).length ? (p.categorias || []).map(c => c.nombre).join(', ') : <span className="sin-cat">Sin categoría</span>}</td>
        <td>{p.proveedor_nombre || <span className="sin-cat">Sin distribuidora</span>}</td>
        <td>{p.stock === 0 ? <span className="badge out">Sin stock</span> : <span className="badge ok">Disponible</span>}</td>
        <td><button onClick={() => openEdit(p)}>editar</button></td></tr>)}
      </tbody></table></div>
    <Modal open={catOpen} onClose={() => setCatOpen(false)} title="Nueva categoría">
      <Field label="Nombre" error={catNombre ? errNombre(catNombre, 2) : ''}>
        <input placeholder="Nombre" value={catNombre} onChange={e => setCatNombre(e.target.value)} className={catNombre && errNombre(catNombre, 2) ? 'invalid' : ''} />
      </Field>
      <Field label="Descripción"><input placeholder="Descripción" value={catDesc} onChange={e => setCatDesc(e.target.value)} /></Field>
      <div className="modal-actions"><button className="ghost" onClick={() => setCatOpen(false)}>Cancelar</button><button onClick={async () => { if (errNombre(catNombre, 2)) return; try { const nc = await api.createCat({ nombre: catNombre.trim(), descripcion: catDesc || null }); setAllCats(await api.cats().catch(() => [])); setCat(String(nc.id)); setCatOpen(false); load(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
    </Modal>
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo producto" wide>
      <p className="muted small">El stock inicial es 0 y se actualiza solo al ingresar pedido por Distribuidoras.</p>
      <div className="grid">
        <Field label="SKU" hint="Código único del producto, opcional" error={(form.sku || '').length > 60 ? 'Máximo 60 caracteres' : ''}><input placeholder="Ej: RC-MINI-3KG" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} /></Field>
        <Field label="Nombre*" hint="Nombre visible en listados y ventas" error={errNombre(form.nombre, 2)}><input placeholder="Ej: Royal Canin Mini 3kg" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} className={errNombre(form.nombre, 2) ? 'invalid' : ''} /></Field>
        <Field label="Marca" hint="Marca o laboratorio"><input placeholder="Ej: Royal Canin" value={form.marca} onChange={e => setForm({ ...form, marca: e.target.value })} /></Field>
        <Field label="Unidad" hint="Cómo se vende y descuenta el stock"><select value={form.unidad} onChange={e => setForm({ ...form, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select></Field>
        <Field label="Precio al costo" hint="Precio de compra, solo referencia interna" error={errMayorIgual0(form.precio_costo)}><input type="number" placeholder="0" value={form.precio_costo} onChange={e => setForm({ ...form, precio_costo: e.target.value })} className={errMayorIgual0(form.precio_costo) ? 'invalid' : ''} /></Field>
        <Field label="Precio venta*" hint="Precio al público que se cobra" error={errMayor0(form.precio_venta, 'Debe ser mayor a 0')}><input type="number" placeholder="100" value={form.precio_venta} onChange={e => setForm({ ...form, precio_venta: e.target.value })} className={errMayor0(form.precio_venta) ? 'invalid' : ''} /></Field>
        <Field label="Precio efect/transf" hint="Venta con 10% off"><input value={precioEfForm === '—' ? '' : `$${precioEfForm}`} disabled readOnly placeholder="—" /></Field>
        <Field label="Mín" hint="Avisa stock bajo al llegar a este nivel" error={errEnteroMin(form.stock_minimo, 0)}><input type="number" placeholder="10" value={form.stock_minimo} onChange={e => setForm({ ...form, stock_minimo: e.target.value })} className={errEnteroMin(form.stock_minimo, 0) ? 'invalid' : ''} /></Field>
        <Field label="Descripción" hint="Detalle largo del producto"><input placeholder="Ej: Alimento para perro adulto" value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} /></Field>
      </div>
      <p>Categorías (opcional, puede quedar Sin categoría): {allCats.map(c => <label key={c.id}><input type="checkbox" checked={form.categoria_ids.includes(c.id)} onChange={e => setForm({ ...form, categoria_ids: e.target.checked ? [...form.categoria_ids, c.id] : form.categoria_ids.filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <Field label="Distribuidora principal" hint="Distribuidora habitual, opcional">
        <select value={form.proveedor_id} onChange={e => { const v = e.target.value; setForm({ ...form, proveedor_id: v, proveedor_ids_alt: v ? Array.from(new Set([...(form.proveedor_ids_alt || []), +v])) : form.proveedor_ids_alt }); }}>
          <option value="">Sin distribuidora</option>{allProvs.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
        </select>
      </Field>
      <p>Otras distribuidoras (opcional): {allProvs.map(p => <label key={p.id}><input type="checkbox" checked={(form.proveedor_ids_alt || []).includes(p.id)} onChange={e => setForm({ ...form, proveedor_ids_alt: e.target.checked ? [...(form.proveedor_ids_alt || []), p.id] : (form.proveedor_ids_alt || []).filter(x => x !== p.id) })} />{p.nombre}</label>)}</p>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={crear}>Guardar</button></div>
    </Modal>
    <Modal open={!!editProd} onClose={() => setEditProd(null)} title={editProd ? `Editar · ${editProd.nombre}` : 'Editar'} wide>
      <p className="muted small">Stock actual: <b>{editProd?.stock}</b> (se actualiza solo al ingresar pedido por Distribuidoras)</p>
      <div className="grid">
        <Field label="Codigo" error={(editForm.sku || '').length > 60 ? 'Máximo 60 caracteres' : ''}><input placeholder="Ej: RC-MINI-3KG" value={editForm.sku || ''} onChange={e => setEditForm({ ...editForm, sku: e.target.value })} /></Field>
        <Field label="Nombre" error={errNombre(editForm.nombre || '', 2)}><input placeholder="Ej: Royal Canin Mini 3kg" value={editForm.nombre || ''} onChange={e => setEditForm({ ...editForm, nombre: e.target.value })} className={errNombre(editForm.nombre || '', 2) ? 'invalid' : ''} /></Field>
        <Field label="Marca"><input placeholder="Ej: Royal Canin" value={editForm.marca || ''} onChange={e => setEditForm({ ...editForm, marca: e.target.value })} /></Field>
        <Field label="Unidad"><select value={editForm.unidad || 'unidad'} onChange={e => setEditForm({ ...editForm, unidad: e.target.value })}><option>unidad</option><option>kg</option><option>lt</option><option>pack</option></select></Field>
        <Field label="Precio al costo" hint="Precio de compra" error={errMayorIgual0(editForm.precio_costo ?? 0)}><input type="number" placeholder="0" value={editForm.precio_costo ?? 0} onChange={e => setEditForm({ ...editForm, precio_costo: e.target.value })} className={errMayorIgual0(editForm.precio_costo ?? 0) ? 'invalid' : ''} /></Field>
        <Field label="Precio venta" hint="Precio al público" error={errMayor0(editForm.precio_venta ?? 0, 'Debe ser mayor a 0')}><input type="number" placeholder="0" value={editForm.precio_venta ?? 0} onChange={e => setEditForm({ ...editForm, precio_venta: e.target.value })} className={errMayor0(editForm.precio_venta ?? 0) ? 'invalid' : ''} /></Field>
        <Field label="Precio efect/transf" hint="Venta con 10% off"><input value={precioEfEdit === '—' ? '' : `$${precioEfEdit}`} disabled readOnly placeholder="—" /></Field>
        <Field label="Mín" hint="Avisa stock bajo al llegar a este minimo" error={errEnteroMin(editForm.stock_minimo ?? 10, 0)}><input type="number" placeholder="10" value={editForm.stock_minimo ?? 10} onChange={e => setEditForm({ ...editForm, stock_minimo: e.target.value })} className={errEnteroMin(editForm.stock_minimo ?? 10, 0) ? 'invalid' : ''} /></Field>
        <Field label="Descripción"><input placeholder="Ej: Alimento para perro adulto" value={editForm.descripcion || ''} onChange={e => setEditForm({ ...editForm, descripcion: e.target.value })} /></Field>
      </div>
      <p>Categorías: {allCats.map(c => <label key={c.id}><input type="checkbox" checked={(editForm.categoria_ids || []).includes(c.id)} onChange={e => setEditForm({ ...editForm, categoria_ids: e.target.checked ? [...(editForm.categoria_ids || []), c.id] : (editForm.categoria_ids || []).filter(x => x !== c.id) })} />{c.nombre}</label>)}</p>
      <Field label="Distribuidora principal" hint="Distribuidora habitual, opcional">
        <select value={editForm.proveedor_id || ''} onChange={e => { const v = e.target.value; setEditForm({ ...editForm, proveedor_id: v, proveedor_ids_alt: v ? Array.from(new Set([...(editForm.proveedor_ids_alt || []), +v])) : editForm.proveedor_ids_alt }); }}>
          <option value="">Sin distribuidora</option>{allProvs.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
        </select>
      </Field>
      <p>Otras distribuidoras (opcional): {allProvs.map(p => <label key={p.id}><input type="checkbox" checked={(editForm.proveedor_ids_alt || []).includes(p.id)} onChange={e => setEditForm({ ...editForm, proveedor_ids_alt: e.target.checked ? [...(editForm.proveedor_ids_alt || []), p.id] : (editForm.proveedor_ids_alt || []).filter(x => x !== p.id) })} />{p.nombre}</label>)}</p>
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
function ProdBuscador({ prods, value, onChange, allowSinStock = false }) {
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
              className={'sug-item' + (!allowSinStock && p.stock === 0 ? ' disabled' : '')}
              onMouseDown={(allowSinStock || p.stock > 0) ? () => { onChange(p.id); setQuery(p.nombre); setOpen(false); } : e => e.preventDefault()}
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
  const [tried, setTried] = useState(false);

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
    setTried(false);
    setShowNuevoCliente(false);
    setNuevoClienteErr('');
  };

  const submit = async () => {
    setTried(true);
    if (!f.cliente_id) return;
    if (lineas.some(l => !l.producto_id)) return;
    if (lineas.some(l => errEnteroMin(l.cantidad, 1) || errDtoValor(l.descuento_tipo, l.descuento_valor))) return;
    if (errDtoValor(f.descuento_tipo, f.descuento_valor)) return;
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
    const eN = errNombre(nuevoClienteForm.nombre, 2);
    const eE = !nuevoClienteForm.email.trim() ? 'Completá este campo' : !isEmailOk(nuevoClienteForm.email) ? 'Email inválido' : '';
    const eD = !nuevoClienteForm.dni.trim() ? 'Completá este campo' : nuevoClienteForm.dni.trim().length < 7 ? 'Mínimo 7 caracteres' : '';
    if (eN || eE || eD) { setNuevoClienteErr(`Corregí lo marcado en rojo: ${eN || eE || eD}`); return; }
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

  const eCliente = (!f.cliente_id && (tried || clienteQuery.trim())) ? 'Elegí un cliente o crealo' : '';
  const eDtoPedido = errDtoValor(f.descuento_tipo, f.descuento_valor);

  return <section>
    <div className="sec-head"><h2>Ventas · Hoy</h2></div>
    <Err e={err} />
    <div className="sale-box">
      <h3>Registrar venta</h3>
      <div className="row">
        {/* Buscador de clientes con dropdown */}
        <Field label="Cliente" error={eCliente}>
          <div className="autocomplete-wrap">
            <input
              placeholder="Buscar cliente por nombre..."
              value={clienteQuery}
              autoComplete="off"
              onChange={e => { setClienteQueryP(e.target.value); setFP(prev => ({ ...prev, cliente_id: '' })); setClienteOpen(true); }}
              onFocus={() => { if (clienteQuery.trim()) setClienteOpen(true); }}
              onBlur={() => setTimeout(() => setClienteOpen(false), 150)}
              className={eCliente ? 'invalid' : ''}
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
        <Field label="Método de pago"><select value={f.metodo_pago} onChange={e => { const v = e.target.value; setFP(prev => (['efectivo', 'transferencia'].includes(v) && prev.descuento_tipo === 'ningun' ? { ...prev, metodo_pago: v, descuento_tipo: 'porcentaje', descuento_valor: 10 } : { ...prev, metodo_pago: v })); }}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></Field>
        <Field label="Descuento del pedido"><select value={f.descuento_tipo} onChange={e => setFP({ ...f, descuento_tipo: e.target.value })}><option value="ningun">sin dto</option><option value="porcentaje">% pedido</option><option value="monto_fijo">$ pedido</option></select></Field>
        <Field label="Valor del descuento" hint="Si no hay dto, 0" error={eDtoPedido}><input type="number" value={f.descuento_valor} onChange={e => setFP({ ...f, descuento_valor: e.target.value })} className={eDtoPedido ? 'invalid' : ''} /></Field>
      </div>
      {lineas.map((l, i) => {
        const eCant = errEnteroMin(l.cantidad, 1);
        const eDtoL = errDtoValor(l.descuento_tipo, l.descuento_valor);
        return <div className="line" key={i}>
        <Field className="lp" label="Producto" hint="Con stock disponible" error={!l.producto_id ? 'Elegí un producto' : ''}>
          <ProdBuscador prods={prods} value={l.producto_id} onChange={id => setLineasP(lineas.map((x, j) => j === i ? { ...x, producto_id: id } : x))} />
        </Field>
        <Field className="lc" label="Cantidad" hint="Unidades" error={eCant}><input type="number" min="1" value={l.cantidad} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, cantidad: e.target.value } : x))} className={eCant ? 'invalid' : ''} /></Field>
        <Field className="ld" label="Descuento por producto"><select value={l.descuento_tipo} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, descuento_tipo: e.target.value } : x))}><option value="ningun">sin dto</option><option value="porcentaje">%</option><option value="monto_fijo">$</option></select></Field>
        <Field className="lv" label="Valor" hint="Del dto línea" error={eDtoL}><input type="number" value={l.descuento_valor} onChange={e => setLineasP(lineas.map((x, j) => j === i ? { ...x, descuento_valor: e.target.value } : x))} className={eDtoL ? 'invalid' : ''} /></Field>
        {/* Solo mostrar el botón quitar si hay más de 1 línea */}
        {lineas.length > 1 && (
          <button className="ghost" title="Quitar producto" onClick={() => setLineasP(lineas.filter((_, j) => j !== i))}>-</button>
        )}
      </div>; })}
      <div className="modal-actions">
        <button className="ghost" onClick={() => setLineasP([...lineas, { producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }])}>Agregar producto</button>
        <span style={{ flex: 1 }} />
        <button onClick={submit}>Guardar venta</button>
      </div>
    </div>
    <h3>Ventas de hoy</h3>
    {pedidos.length === 0 ? <p className="muted">Todavía no hay ventas hoy.</p> :
      <ul>{pedidos.map(p => <li key={p.id}>#{p.id} · {cliNombre(p.cliente_id)} · ${p.total} · {p.estado} · {MEDIO_TXT[p.metodo_pago] || p.metodo_pago}<br />
        <small>{(p.detalles || []).map(d => `${d.nombre_snapshot} x${d.cantidad}`).join(' · ')}</small>
        {p.estado === 'pagado' && <button onClick={() => cancelar(p)}>cancelar</button>}</li>)}</ul>}

    {/* Modal nuevo cliente — abre centrado y ocupa el ancho completo del modal */}
    <Modal open={showNuevoCliente} onClose={() => { setShowNuevoCliente(false); setNuevoClienteErr(''); }} title="Nuevo cliente" wide>
      <div className="grid">
        <Field label="Nombre*" hint="Nombre y apellido" error={errNombre(nuevoClienteForm.nombre, 2)}><input placeholder="Martina López" value={nuevoClienteForm.nombre} onChange={e => setNuevoClienteForm(prev => ({ ...prev, nombre: e.target.value }))} className={errNombre(nuevoClienteForm.nombre, 2) ? 'invalid' : ''} /></Field>
        <Field label="Email*" hint="Email único del cliente" error={!nuevoClienteForm.email ? '' : !isEmailOk(nuevoClienteForm.email) ? 'Email inválido' : ''}><input type="email" placeholder="martina@mail.com" value={nuevoClienteForm.email} onChange={e => setNuevoClienteForm(prev => ({ ...prev, email: e.target.value }))} className={nuevoClienteForm.email && !isEmailOk(nuevoClienteForm.email) ? 'invalid' : ''} /></Field>
        <Field label="Teléfono" hint="Opcional"><input placeholder="351-2345678" value={nuevoClienteForm.telefono} onChange={e => setNuevoClienteForm(prev => ({ ...prev, telefono: e.target.value }))} /></Field>
        <Field label="DNI*" hint="DNI único del cliente" error={!nuevoClienteForm.dni ? '' : nuevoClienteForm.dni.trim().length < 7 ? 'Mínimo 7 caracteres' : ''}><input placeholder="30123456" value={nuevoClienteForm.dni} onChange={e => setNuevoClienteForm(prev => ({ ...prev, dni: e.target.value }))} className={nuevoClienteForm.dni && nuevoClienteForm.dni.trim().length < 7 ? 'invalid' : ''} /></Field>
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
  const [selCli, setSelCli] = useState(null);
  const [peds, setPeds] = useState([]);
  const [page, setPage] = useState(0);
  const [detId, setDetId] = useState(null); // pedido con detalle desplegado
  const PAGE = 5;

  const verPeds = async (c) => {
    try {
      const list = await api.pedidosCliente(c.id);
      setSelCli(c); setPeds(list); setPage(0); setDetId(null);
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
            <b>📅 {fechaFmt(p.fecha)}</b> · pedido #{p.id} · {p.estado} · {MEDIO_TXT[p.metodo_pago] || p.metodo_pago}
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
      <input placeholder="Buscar nombre, email o DNI" value={q} onChange={e => setQ(e.target.value)} style={{ flex: '1 1 300px' }} />
    </div>
    <Modal open={open} onClose={() => setOpen(false)} title="Nuevo cliente">
      <div className="grid">
        <Field label="Nombre" hint="Nombre y apellido del cliente" error={errNombre(f.nombre, 2)}><input placeholder="Ej: Martina López" value={f.nombre} onChange={e => setF({ ...f, nombre: e.target.value })} className={errNombre(f.nombre, 2) ? 'invalid' : ''} /></Field>
        <Field label="Email" hint="Email único, identifica al cliente" error={!f.email ? '' : !isEmailOk(f.email) ? 'Email inválido' : ''}><input placeholder="Ej: martina@mail.com" value={f.email} onChange={e => setF({ ...f, email: e.target.value })} className={f.email && !isEmailOk(f.email) ? 'invalid' : ''} /></Field>
        <Field label="Teléfono" hint="Teléfono de contacto, opcional"><input placeholder="Ej: 351-2345678" value={f.telefono} onChange={e => setF({ ...f, telefono: e.target.value })} /></Field>
        <Field label="DNI" hint="DNI único del cliente" error={!f.dni ? '' : f.dni.trim().length < 7 ? 'Mínimo 7 caracteres' : ''}><input placeholder="Ej: 30123456" value={f.dni} onChange={e => setF({ ...f, dni: e.target.value })} className={f.dni && f.dni.trim().length < 7 ? 'invalid' : ''} /></Field>
        <Field label="Dirección" hint="Dirección, opcional"><input placeholder="Ej: Av Colón 1234" value={f.direccion} onChange={e => setF({ ...f, direccion: e.target.value })} /></Field>
      </div>
      <div className="modal-actions"><button className="ghost" onClick={() => setOpen(false)}>Cancelar</button><button onClick={async () => { const hayErr = errNombre(f.nombre, 2) || (!f.email.trim() ? 'Completá el email' : !isEmailOk(f.email) ? 'Email inválido' : '') || (!f.dni.trim() ? 'Completá el DNI' : f.dni.trim().length < 7 ? 'DNI mínimo 7' : ''); if (hayErr) { alert(`Corregí lo marcado en rojo: ${hayErr}`); return; } try { await api.createCliente(f); setF({ nombre: '', email: '', telefono: '', dni: '', direccion: '' }); setOpen(false); reload(); } catch (e) { alert(e.message); } }}>Guardar</button></div>
    </Modal>
    <div className="tbl-wrap"><table><thead><tr><th>Nombre</th><th>Email</th><th>DNI</th><th>Teléfono</th><th>Dirección</th><th>Acciones</th></tr></thead>
      {rows.map(c => <tbody key={c.id}>
        <tr>
          <td>{c.nombre}</td><td>{c.email}</td><td>{c.dni}</td>
          <td>{c.telefono || '-'}</td><td>{c.direccion || '-'}</td>
          <td><button onClick={() => verPeds(c)}>ver pedidos</button></td>
        </tr>
      </tbody>)}
    </table></div>
    {rows.length === 0 && <p className="muted">Sin clientes para este filtro.</p>}
    <Modal open={!!selCli} onClose={() => setSelCli(null)} title={selCli ? `Pedidos · ${selCli.nombre}` : 'Pedidos'} wide>
      {pedsBlock}
      <div className="modal-actions"><button className="ghost" onClick={() => setSelCli(null)}>Cerrar</button></div>
    </Modal>
  </section>;
}

/* ---------- Caja diaria (paso 3) ---------- */
function Caja() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [dia, setDia] = useState(hoy);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState('');
  const [f, setF] = useState({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' });

  const load = async (d) => {
    setErr('');
    try { setRes(await api.caja(d)); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { load(dia); }, []);
  const mover = (d) => {
    const dt = new Date(dia + 'T12:00:00'); dt.setDate(dt.getDate() + d);
    const s = dt.toISOString().slice(0, 10); setDia(s); load(s);
  };
  const guardar = async () => {
    if (!f.descripcion.trim() || !(+f.monto > 0)) { setErr('Descripción y monto mayor a 0'); return; }
    try {
      await api.createCajaMov({ tipo: f.tipo, medio: f.medio, descripcion: f.descripcion.trim(), monto: +f.monto });
      setF({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' }); load(dia);
    } catch (e) { setErr(e.message); }
  };
  const borrar = async (m) => {
    if (!confirm(`Borrar "${m.descripcion}"?`)) return;
    try { await api.deleteCajaMov(m.id); load(dia); } catch (e) { setErr(e.message); }
  };
  const fmt = (n) => '$' + (+n).toLocaleString('es-AR', { minimumFractionDigits: 2 });
  const movs = res?.movimientos || [];
  const entradas = movs.filter(m => m.tipo === 'ENTRADA');
  const salidas = movs.filter(m => m.tipo === 'SALIDA');
  return <section>
    <div className="sec-head"><h2>{dia === hoy ? 'Historial' : `Historial · ${dia}`}</h2>{dia === hoy
      ? <button className="fab" disabled>Hoy</button>
      : <button className="fab" onClick={() => { setDia(hoy); load(hoy); }}>‹ Volver a hoy</button>}</div>
    <Err e={err} />
    <div className="row day-picker">
      <button className="ghost" onClick={() => mover(-1)}>‹ Ayer</button>
      <input type="date" value={dia} max={hoy} onChange={e => { setDia(e.target.value); load(e.target.value); }} />
      <button className="ghost" onClick={() => mover(1)} disabled={dia >= hoy}>Mañana ›</button>
    </div>
    <div className="cards">
      <div className="card"><span>Entrada</span><b>{fmt(res?.total_entrada || 0)}</b><small>{entradas.length} movimientos</small></div>
      <div className="card"><span>Salida</span><b>{fmt(res?.total_salida || 0)}</b><small>{salidas.length} movimientos</small></div>
      <div className="card"><span>Balance</span><b>{fmt(res?.balance || 0)}</b><small>entrada − salida</small></div>
    </div>
    <div className="sale-box">
      <h3>Movimiento manual (gastos, entradas extra)</h3>
      <p className="muted small">Las ventas y los pagos a distribuidoras se registran solos.</p>
      <div className="row">
        <Field label="Tipo"><select value={f.tipo} onChange={e => setF({ ...f, tipo: e.target.value })}><option value="SALIDA">salida</option><option value="ENTRADA">entrada</option></select></Field>
        <Field label="Método de pago"><select value={f.medio} onChange={e => setF({ ...f, medio: e.target.value })}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></Field>
        <Field label="Descripción"><input placeholder="Ej: Cabify" value={f.descripcion} onChange={e => setF({ ...f, descripcion: e.target.value })} /></Field>
        <Field label="Monto"><input type="number" placeholder="0" value={f.monto} onChange={e => setF({ ...f, monto: e.target.value })} /></Field>
        <button onClick={guardar}>Agregar</button>
      </div>
    </div>
    <div className="cols">
      <div>
        <h3>Entradas</h3>
        {entradas.length === 0 ? <p className="muted">Sin entradas.</p> :
          <ul>{entradas.map(m => <li key={m.id}>{m.descripcion} · {fmt(m.monto)} <small>· {MEDIO_TXT[m.medio] || m.medio}</small></li>)}</ul>}
      </div>
      <div>
        <h3>Salidas</h3>
        {salidas.length === 0 ? <p className="muted">Sin salidas.</p> :
          <ul>{salidas.map(m => <li key={m.id}>{m.descripcion} · {fmt(m.monto)} <small>· {MEDIO_TXT[m.medio] || m.medio}</small>
            {!m.automatico && <button onClick={() => borrar(m)}>borrar</button>}</li>)}</ul>}
      </div>
    </div>
  </section>;
}

/* ---------- Hoy eliminado: su contenido vive en Principal (Ventas + Caja) ---------- */
