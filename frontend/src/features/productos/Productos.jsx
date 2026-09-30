import { useEffect, useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import { errNombre, errMayor0, errMayorIgual0, errEnteroMin } from '../../utils/validators';

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

export default Productos;
