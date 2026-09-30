import { useEffect, useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import ProdBuscador from '../../components/ProdBuscador';
import { MEDIO_TXT, MEDIO_SHORT, MEDIOS_SEL } from '../../constants/paymentMethods';
import { errNombre, errEnteroMin, errDtoValor, isEmailOk } from '../../utils/validators';
import { ventasState } from './ventasState';
import { todayLocal } from '../../utils/dates';

function Ventas() {
  const hoy = todayLocal();
  const [clientes, setClientes] = useState([]);
  const [prods, setProds] = useState([]);
  const [pedidos, setPedidos] = useState([]);
  const [err, setErr] = useState('');

  // Persistir estado del formulario entre cambios de pestaña usando objeto externo
  const [f, setF] = useState(() => ventasState.f);
  const [lineas, setLineas] = useState(() => ventasState.lineas);
  const [clienteQuery, setClienteQuery] = useState(() => ventasState.clienteQuery);
  const [pagos, setPagos] = useState(() => ventasState.pagos);
  const [busy, setBusy] = useState(false);

  // Sincronizar con ventasState en cada cambio
  const setFP = v => { const val = typeof v === 'function' ? v(f) : v; ventasState.f = val; setF(val); };
  const setLineasP = v => { const val = typeof v === 'function' ? v(lineas) : v; ventasState.lineas = val; setLineas(val); };
  const setClienteQueryP = v => { ventasState.clienteQuery = v; setClienteQuery(v); };
  const setPagosP = v => { const val = typeof v === 'function' ? v(pagos) : v; ventasState.pagos = val; setPagos(val); };

  // Total estimado (espeja el cálculo del backend para validar el pago mixto)
  const aplicarDtoEst = (base, tipo, valor) => {
    const b = +base || 0, v = +valor || 0;
    if (tipo === 'ningun' || v === 0) return Math.round(b * 100) / 100;
    if (tipo === 'porcentaje') return Math.round(b * (1 - v / 100) * 100) / 100;
    return Math.round((b - v) * 100) / 100;
  };
  const totalEst = (() => {
    let sub = 0;
    for (const l of lineas) {
      const p = prods.find(x => String(x.id) === String(l.producto_id));
      if (!p || !(+l.cantidad >= 1)) continue;
      sub = Math.round((sub + aplicarDtoEst((+p.precio_venta || 0) * (+l.cantidad || 0), l.descuento_tipo, +l.descuento_valor || 0)) * 100) / 100;
    }
    return aplicarDtoEst(sub, f.descuento_tipo, +f.descuento_valor || 0);
  })();
  const cargado = Math.round(pagos.reduce((a, p) => a + (+p.monto || 0), 0) * 100) / 100;
  const restante = Math.round((totalEst - cargado) * 100) / 100;
  const pagosOk = pagos.length > 0 && pagos.length <= 5
    && pagos.every(p => p.metodo && Number.isFinite(+p.monto) && +p.monto > 0)
    && Math.abs(restante) <= 0.01;
  const pagoTxt = (p) => p.es_mixto && (p.pagos || []).length > 1
    ? p.pagos.map(x => `${MEDIO_SHORT[x.metodo] || x.metodo} $${(+x.monto).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`).join(' + ')
    : (MEDIO_TXT[p.metodo_pago] || p.metodo_pago);

  const [clienteOpen, setClienteOpen] = useState(false);
  const [tried, setTried] = useState(false);

  // Modal nuevo cliente
  const [showNuevoCliente, setShowNuevoCliente] = useState(false);
  const [nuevoClienteForm, setNuevoClienteForm] = useState({ nombre: '', email: '', telefono: '', dni: '', direccion: '', mascotas: [] });
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
    const pagosInit = [{ metodo: 'efectivo', monto: '' }];
    ventasState.f = fInit; setF(fInit);
    ventasState.lineas = lineasInit; setLineas(lineasInit);
    ventasState.clienteQuery = ''; setClienteQuery('');
    ventasState.pagos = pagosInit; setPagos(pagosInit);
    setTried(false);
    setShowNuevoCliente(false);
    setNuevoClienteErr('');
  };

  const submit = async () => {
    setTried(true);
    if (busy) return;
    if (!f.cliente_id) return;
    if (lineas.some(l => !l.producto_id)) return;
    if (lineas.some(l => errEnteroMin(l.cantidad, 1) || errDtoValor(l.descuento_tipo, l.descuento_valor))) return;
    if (errDtoValor(f.descuento_tipo, f.descuento_valor)) return;
    if (!pagosOk) return;
    setBusy(true);
    try {
      const r = await api.createPedido({ cliente_id: +f.cliente_id, metodo_pago: pagos[0].metodo, descuento_tipo: f.descuento_tipo, descuento_valor: +f.descuento_valor, detalles: lineas.map(l => ({ producto_id: +l.producto_id, cantidad: +l.cantidad, descuento_tipo: l.descuento_tipo, descuento_valor: +l.descuento_valor })), pagos: pagos.map(p => ({ metodo: p.metodo, monto: +p.monto })) });
      alert(`Venta #${r.id} registrada · total $${r.total}`); resetPedido(); load();
    } catch (e) { alert(e.message); } finally { setBusy(false); }
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
      const nuevo = await api.createCliente({ ...nuevoClienteForm, mascotas: (nuevoClienteForm.mascotas || []).filter(m => m.nombre.trim()) });
      const lista = await api.clientes();
      setClientes(lista);
      setFP(prev => ({ ...prev, cliente_id: nuevo.id }));
      setClienteQueryP(nuevo.nombre);
      setShowNuevoCliente(false);
      setClienteOpen(false);
      setNuevoClienteForm({ nombre: '', email: '', telefono: '', dni: '', direccion: '', mascotas: [] });
    } catch (e) { setNuevoClienteErr(e.message); }
  };

  const eCliente = (!f.cliente_id && (tried || clienteQuery.trim())) ? 'Elegí un cliente o crealo' : '';
  const eDtoPedido = errDtoValor(f.descuento_tipo, f.descuento_valor);
  const fmt = (n) => '$' + (+(n || 0)).toLocaleString('es-AR', { minimumFractionDigits: 2 });

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
      <h3>Pagos</h3>
      {pagos.map((p, i) => {
        const eMonto = tried && !(Number.isFinite(+p.monto) && +p.monto > 0) ? 'Monto mayor a 0' : '';
        return <div className="line" key={i}>
          <Field className="lp" label={`Medio ${i + 1}`}>
            <select value={p.metodo} onChange={e => setPagosP(pagos.map((x, j) => j === i ? { ...x, metodo: e.target.value } : x))}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
          </Field>
          <Field className="lc" label="Monto" hint="Mayor a 0" error={eMonto}><input type="number" min="0.01" step="0.01" value={p.monto} onChange={e => setPagosP(pagos.map((x, j) => j === i ? { ...x, monto: e.target.value } : x))} className={eMonto ? 'invalid' : ''} /></Field>
          {pagos.length > 1 && (
            <button className="ghost" title="Quitar pago" onClick={() => setPagosP(pagos.filter((_, j) => j !== i))}>-</button>
          )}
        </div>; })}
      <div className="modal-actions">
        {pagos.length < 5 && <button className="ghost" onClick={() => setPagosP([...pagos, { metodo: f.metodo_pago, monto: '' }])}>Agregar pago</button>}
        <span style={{ flex: 1 }} />
        <span className="muted small">Total: <b>{fmt(totalEst)}</b> · Cargado: <b>{fmt(cargado)}</b> · {Math.abs(restante) <= 0.01 ? 'Cuadra ✓' : restante > 0 ? `Faltan ${fmt(restante)}` : `Sobran ${fmt(-restante)}`}</span>
      </div>
      {tried && !pagosOk && <p className="err">Los pagos deben sumar el total de la venta, con montos mayores a 0.</p>}
      <div className="modal-actions">
        <button className="ghost" onClick={() => setLineasP([...lineas, { producto_id: '', cantidad: 1, descuento_tipo: 'ningun', descuento_valor: 0 }])}>Agregar producto</button>
        <span style={{ flex: 1 }} />
        <button onClick={submit} disabled={busy}>{busy ? 'Guardando...' : 'Guardar venta'}</button>
      </div>
    </div>
    <h3>Ventas de hoy {pedidos.length > 0 && <span className="muted">· {pedidos.length}</span>}</h3>
    {pedidos.length === 0 ? <p className="muted">Todavía no hay ventas hoy.</p> :
      <ul className="peds-list">{pedidos.map(p => {
        const dets = p.detalles || [];
        return <li key={p.id} className="ped-card">
          <div className="ped-head">
            <b>#{p.id} · {cliNombre(p.cliente_id)}</b>
            <b className="in">{fmt(p.total)}</b>
          </div>
          <div className="muted small ped-meta">{pagoTxt(p)} · {dets.length} producto{dets.length === 1 ? '' : 's'}{p.vendedora_nombre ? ` · Vendedora: ${p.vendedora_nombre}` : ''}</div>
          {dets.length > 0 && <div className="det">
            {dets.map((d, i) => <div className="det-line" key={i}>
              <span>{d.nombre_snapshot} ×{d.cantidad}</span>
              <span>{fmt(d.subtotal_linea)}</span>
            </div>)}
          </div>}
          <div className="ped-foot">
            <span className="ped-badges">
              {p.estado === 'pagado'
                ? <span className="badge ok">Pagada</span>
                : <span className="badge out">{p.estado}</span>}
            </span>
            <span className="ped-actions">
              {p.estado === 'pagado' && <button onClick={() => cancelar(p)}>cancelar</button>}
            </span>
          </div>
        </li>; })}</ul>}

    {/* Modal nuevo cliente — abre centrado y ocupa el ancho completo del modal */}
    <Modal open={showNuevoCliente} onClose={() => { setShowNuevoCliente(false); setNuevoClienteErr(''); }} title="Nuevo cliente" wide>
      <div className="grid">
        <Field label="Nombre*" hint="Nombre y apellido" error={errNombre(nuevoClienteForm.nombre, 2)}><input placeholder="Martina López" value={nuevoClienteForm.nombre} onChange={e => setNuevoClienteForm(prev => ({ ...prev, nombre: e.target.value }))} className={errNombre(nuevoClienteForm.nombre, 2) ? 'invalid' : ''} /></Field>
        <Field label="Email*" hint="Email único del cliente" error={!nuevoClienteForm.email ? '' : !isEmailOk(nuevoClienteForm.email) ? 'Email inválido' : ''}><input type="email" placeholder="martina@mail.com" value={nuevoClienteForm.email} onChange={e => setNuevoClienteForm(prev => ({ ...prev, email: e.target.value }))} className={nuevoClienteForm.email && !isEmailOk(nuevoClienteForm.email) ? 'invalid' : ''} /></Field>
        <Field label="Teléfono" hint="Opcional"><input placeholder="351-2345678" value={nuevoClienteForm.telefono} onChange={e => setNuevoClienteForm(prev => ({ ...prev, telefono: e.target.value }))} /></Field>
        <Field label="DNI*" hint="DNI único del cliente" error={!nuevoClienteForm.dni ? '' : nuevoClienteForm.dni.trim().length < 7 ? 'Mínimo 7 caracteres' : ''}><input placeholder="30123456" value={nuevoClienteForm.dni} onChange={e => setNuevoClienteForm(prev => ({ ...prev, dni: e.target.value }))} className={nuevoClienteForm.dni && nuevoClienteForm.dni.trim().length < 7 ? 'invalid' : ''} /></Field>
        <Field label="Dirección" hint="Opcional"><input placeholder="Av Colón 1234" value={nuevoClienteForm.direccion} onChange={e => setNuevoClienteForm(prev => ({ ...prev, direccion: e.target.value }))} /></Field>
      </div>
      <h3>Mascotas <span className="muted small">(opcional)</span></h3>
      {(nuevoClienteForm.mascotas || []).map((m, i) => <div className="line" key={i}>
        <Field className="lc" label="Tipo"><select value={m.especie} onChange={e => setNuevoClienteForm(prev => ({ ...prev, mascotas: prev.mascotas.map((x, j) => j === i ? { ...x, especie: e.target.value } : x) }))}><option value="perro">Perro</option><option value="gato">Gato</option></select></Field>
        <Field className="lp" label="Nombre"><input value={m.nombre} onChange={e => setNuevoClienteForm(prev => ({ ...prev, mascotas: prev.mascotas.map((x, j) => j === i ? { ...x, nombre: e.target.value } : x) }))} /></Field>
        <button className="ghost" onClick={() => setNuevoClienteForm(prev => ({ ...prev, mascotas: prev.mascotas.filter((_, j) => j !== i) }))}>-</button>
      </div>)}
      <button className="ghost" onClick={() => setNuevoClienteForm(prev => ({ ...prev, mascotas: [...prev.mascotas, { especie: 'perro', nombre: '' }] }))}>+ Agregar mascota</button>
      {nuevoClienteErr && <p className="err">{nuevoClienteErr}</p>}
      <div className="modal-actions">
        <button className="ghost" onClick={() => { setShowNuevoCliente(false); setNuevoClienteErr(''); }}>Cancelar</button>
        <button onClick={guardarNuevoCliente}>Guardar cliente</button>
      </div>
    </Modal>
  </section>;
}


export default Ventas;
