import { useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import useLoad from '../../hooks/useLoad';
import { MEDIO_TXT } from '../../constants/paymentMethods';
import { errNombre, isEmailOk } from '../../utils/validators';
import { parseApiUtc } from '../../utils/dates';

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
    const d = parseApiUtc(f);
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


export default Clientes;
