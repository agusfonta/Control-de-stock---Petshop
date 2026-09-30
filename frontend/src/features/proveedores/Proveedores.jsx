import { useEffect, useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import ProdBuscador from '../../components/ProdBuscador';
import { MEDIO_TXT, MEDIOS_SEL } from '../../constants/paymentMethods';
import { todayLocal, formatApiDate, apiDateToLocalInput } from '../../utils/dates';

function Proveedores() {
  const hoy = todayLocal();
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
      nro: c.nro_boleta, fecha: apiDateToLocalInput(c.fecha_pedido),
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
        const fechaPed = formatApiDate(c.fecha_pedido);
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
                ? <span className="badge ok">Entregada {formatApiDate(c.fecha_entrega)}</span>
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
        <Field label="Entrega"><input value={edit?.fecha_entrega ? apiDateToLocalInput(edit.fecha_entrega) : 'Sin entregar'} disabled /></Field>
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

export default Proveedores;
