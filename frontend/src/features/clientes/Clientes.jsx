import { useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import useLoad from '../../hooks/useLoad';
import { MEDIO_TXT } from '../../constants/paymentMethods';
import { errNombre, isEmailOk, isPhoneOk } from '../../utils/validators';
import { parseApiUtc } from '../../utils/dates';

const MASCOTA_VACIA = { especie: 'perro', nombre: '' };
const CLIENTE_VACIO = { nombre: '', email: '', telefono: '', dni: '', direccion: '', mascotas: [] };

function Clientes() {
  const { data, err, reload } = useLoad(api.clientes);
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(CLIENTE_VACIO);
  const [q, setQ] = useState('');
  const [menuId, setMenuId] = useState(null);
  const [mascotasCli, setMascotasCli] = useState(null);
  const [selCli, setSelCli] = useState(null);
  const [peds, setPeds] = useState([]);
  const [page, setPage] = useState(0);
  const [detId, setDetId] = useState(null);
  const PAGE = 5;

  const setMascota = (i, patch) => setForm(prev => ({
    ...prev,
    mascotas: prev.mascotas.map((m, j) => j === i ? { ...m, ...patch } : m),
  }));

  const openCreate = () => {
    setEditingId(null);
    setForm(CLIENTE_VACIO);
    setMenuId(null);
    setFormOpen(true);
  };

  const openEdit = c => {
    setEditingId(c.id);
    setForm({
      nombre: c.nombre || '',
      email: c.email || '',
      telefono: c.telefono || '',
      dni: c.dni || '',
      direccion: c.direccion || '',
      mascotas: (c.mascotas || []).map(m => ({ especie: m.especie, nombre: m.nombre })),
    });
    setMenuId(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setForm(CLIENTE_VACIO);
  };

  const validar = () => {
    const nombreErr = errNombre(form.nombre, 2);
    if (nombreErr) return nombreErr;
    if (!form.email.trim()) return 'Completá el email';
    if (!isEmailOk(form.email)) return 'Email inválido';
    if (form.telefono.trim() && !isPhoneOk(form.telefono)) return 'Teléfono inválido';
    if (!form.dni.trim()) return 'Completá el DNI';
    if (form.dni.trim().length < 7) return 'DNI mínimo 7';
    if (form.mascotas.some(m => !m.nombre.trim())) return 'Cada mascota necesita un nombre';
    return '';
  };

  const guardar = async () => {
    const hayErr = validar();
    if (hayErr) {
      alert(`Corregí lo marcado: ${hayErr}`);
      return;
    }
    const payload = {
      ...form,
      telefono: form.telefono.trim() || null,
      mascotas: form.mascotas.map(m => ({ especie: m.especie, nombre: m.nombre.trim() })),
    };
    try {
      if (editingId) await api.updateCliente(editingId, payload);
      else await api.createCliente(payload);
      closeForm();
      await reload();
    } catch (e) {
      alert(e.message);
    }
  };

  const verMascotas = c => {
    setMascotasCli(c);
    setMenuId(null);
  };

  const verPeds = async c => {
    try {
      const list = await api.pedidosCliente(c.id);
      setSelCli(c); setPeds(list); setPage(0); setDetId(null); setMenuId(null);
    } catch (e) { alert(e.message); }
  };

  const dtoTxt = (t, v) => t === 'ningun' ? 'sin dto' : t === 'porcentaje' ? `${v}%` : `$${v}`;
  const fechaFmt = f => {
    if (!f) return '';
    const d = parseApiUtc(f);
    return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };
  const norm = s => (s || '').toLowerCase();
  const rows = (data || []).filter(c => {
    const t = norm(q.trim());
    if (!t) return true;
    return norm(c.nombre).includes(t) || norm(c.email).includes(t) || norm(c.dni).includes(t);
  });
  const totalPages = Math.max(1, Math.ceil(peds.length / PAGE));
  const view = peds.slice(page * PAGE, page * PAGE + PAGE);

  return (
    <section onClick={() => menuId && setMenuId(null)}>
      <div className="sec-head"><h2>Clientes</h2><button className="fab" onClick={openCreate}>+ Nuevo</button></div>
      <Err e={err} />
      <div className="row">
        <input placeholder="Buscar nombre, email o DNI" value={q} onChange={e => setQ(e.target.value)} style={{ flex: '1 1 300px' }} />
      </div>

      <Modal open={formOpen} onClose={closeForm} title={editingId ? 'Editar cliente' : 'Nuevo cliente'}>
        <div className="grid">
          <Field label="Nombre" hint="Nombre y apellido del cliente" error={errNombre(form.nombre, 2)}>
            <input placeholder="Ej: Martina López" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} className={errNombre(form.nombre, 2) ? 'invalid' : ''} />
          </Field>
          <Field label="Email" hint="Email único, identifica al cliente" error={!form.email ? '' : !isEmailOk(form.email) ? 'Email inválido' : ''}>
            <input placeholder="Ej: martina@mail.com" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className={form.email && !isEmailOk(form.email) ? 'invalid' : ''} />
          </Field>
          <Field label="Teléfono" hint="Solo números y formato telefónico válido" error={form.telefono && !isPhoneOk(form.telefono) ? 'Teléfono inválido' : ''}>
            <input placeholder="Ej: 351-2345678" value={form.telefono} onChange={e => setForm({ ...form, telefono: e.target.value })} className={form.telefono && !isPhoneOk(form.telefono) ? 'invalid' : ''} />
          </Field>
          <Field label="DNI" hint="DNI único del cliente" error={!form.dni ? '' : form.dni.trim().length < 7 ? 'Mínimo 7 caracteres' : ''}>
            <input placeholder="Ej: 30123456" value={form.dni} onChange={e => setForm({ ...form, dni: e.target.value })} className={form.dni && form.dni.trim().length < 7 ? 'invalid' : ''} />
          </Field>
          <Field label="Dirección" hint="Dirección, opcional">
            <input placeholder="Ej: Av Colón 1234" value={form.direccion} onChange={e => setForm({ ...form, direccion: e.target.value })} />
          </Field>
        </div>

        <h3>Mascotas <span className="muted small">(opcional)</span></h3>
        {form.mascotas.map((m, i) => (
          <div className="line" key={`${m.id || 'new'}-${i}`}>
            <Field className="lc" label="Tipo"><select value={m.especie} onChange={e => setMascota(i, { especie: e.target.value })}><option value="perro">Perro</option><option value="gato">Gato</option></select></Field>
            <Field className="lp" label="Nombre" error={!m.nombre.trim() ? 'Completá el nombre' : ''}><input value={m.nombre} onChange={e => setMascota(i, { nombre: e.target.value })} placeholder="Luna" /></Field>
            <button className="ghost" onClick={() => setForm(prev => ({ ...prev, mascotas: prev.mascotas.filter((_, j) => j !== i) }))}>-</button>
          </div>
        ))}
        <button className="ghost" onClick={() => setForm(prev => ({ ...prev, mascotas: [...prev.mascotas, { ...MASCOTA_VACIA }] }))}>+ Agregar mascota</button>
        <div className="modal-actions"><button className="ghost" onClick={closeForm}>Cancelar</button><button onClick={guardar}>Guardar</button></div>
      </Modal>

      <div className="tbl-wrap"><table><thead><tr><th>Nombre</th><th>Email</th><th>DNI</th><th>Mascotas</th><th>Teléfono</th><th>Dirección</th><th>Acciones</th></tr></thead>
        <tbody>{rows.map(c => (
          <tr key={c.id}>
            <td>{c.nombre}</td><td>{c.email}</td><td>{c.dni}</td><td>{(c.mascotas || []).length ? `${c.mascotas.length} mascota${c.mascotas.length === 1 ? '' : 's'}` : '-'}</td>
            <td>{c.telefono || '-'}</td><td>{c.direccion || '-'}</td>
            <td>
              <div className="action-menu-wrap">
                <button className="ghost menu-trigger" aria-label={`Acciones de ${c.nombre}`} onClick={e => { e.stopPropagation(); setMenuId(menuId === c.id ? null : c.id); }}>⋯</button>
                {menuId === c.id && <div className="action-menu" onClick={e => e.stopPropagation()}>
                  <button onClick={() => openEdit(c)}>Editar</button>
                  <button onClick={() => verMascotas(c)}>Ver mascotas</button>
                  <button onClick={() => verPeds(c)}>Ver pedidos</button>
                </div>}
              </div>
            </td>
          </tr>
        ))}</tbody>
      </table></div>
      {rows.length === 0 && <p className="muted">Sin clientes para este filtro.</p>}

      <Modal open={!!mascotasCli} onClose={() => setMascotasCli(null)} title={mascotasCli ? `Mascotas · ${mascotasCli.nombre}` : 'Mascotas'}>
        {mascotasCli?.mascotas?.length ? <div className="pets-list">{mascotasCli.mascotas.map(m => <div className="pet-card" key={m.id}><b>{m.nombre}</b><span className="muted">{m.especie === 'perro' ? '🐶 Perro' : '🐱 Gato'}</span></div>)}</div> : <p className="muted">Este cliente no tiene mascotas cargadas.</p>}
      </Modal>

      <Modal open={!!selCli} onClose={() => setSelCli(null)} title={selCli ? `Pedidos · ${selCli.nombre}` : 'Pedidos'} wide>
        <div className="peds">
          {peds.length === 0 ? <p className="muted">Este cliente todavía no tiene pedidos.</p> : <>
            <ul>{view.map(p => <li key={p.id}>
              <b>📅 {fechaFmt(p.fecha)}</b> · pedido #{p.id} · {p.estado} · {MEDIO_TXT[p.metodo_pago] || p.metodo_pago}{p.vendedora_nombre ? ` · Vendedora: ${p.vendedora_nombre}` : ''}
              <button onClick={() => setDetId(detId === p.id ? null : p.id)}>{detId === p.id ? 'ocultar detalle' : 'ver detalle'}</button>
              {detId === p.id && <div className="det">{(p.detalles || []).map(d => <div key={d.id} className="det-line"><span>{d.nombre_snapshot} x{d.cantidad} @ ${d.precio_unitario}</span><span className="muted">dto: {dtoTxt(d.descuento_tipo, d.descuento_valor)} → ${d.subtotal_linea}</span></div>)}<div className="det-total"><span>Subtotal: ${p.subtotal} · Dto pedido: {dtoTxt(p.descuento_tipo, p.descuento_valor)}</span><b>Total: ${p.total} ARS</b></div></div>}
            </li>)}</ul>
            {peds.length > PAGE && <div className="pager"><button className="ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>‹ Nuevos</button><span>{page + 1} / {totalPages}</span><button className="ghost" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Anteriores ›</button></div>}
          </>}
        </div>
        <div className="modal-actions"><button className="ghost" onClick={() => setSelCli(null)}>Cerrar</button></div>
      </Modal>
    </section>
  );
}

export default Clientes;
