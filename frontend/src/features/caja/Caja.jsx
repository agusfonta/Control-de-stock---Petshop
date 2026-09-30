import { useEffect, useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import Modal from '../../components/Modal';
import useLoad from '../../hooks/useLoad';
import { MEDIOS_SEL, MEDIO_SHORT } from '../../constants/paymentMethods';
import { todayLocal, shiftLocalDay, formatApiTime, parseApiUtc } from '../../utils/dates';

function Caja() {
  const hoy = todayLocal();
  const [dia, setDia] = useState(hoy);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' });

  const load = async (d) => {
    if (!d) { setErr('Elegí un día válido'); return; }
    setErr(''); setLoading(true);
    try { setRes(await api.caja(d)); }
    catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { load(dia); }, []);
  const setDiaLoad = (v) => {
    if (!v) return;
    const c = v > hoy ? hoy : v;
    setDia(c); load(c);
  };
  const mover = (d) => {
    if (!dia) return;
    setDiaLoad(shiftLocalDay(dia, d));
  };
  const guardar = async () => {
    if (f.descripcion.trim().length < 2 || !(+f.monto > 0)) { setErr('Descripción (mín 2) y monto mayor a 0'); return; }
    try {
      const payload = { tipo: f.tipo, medio: f.medio, descripcion: f.descripcion.trim(), monto: +f.monto };
      if (dia !== hoy) payload.fecha = `${dia}T12:00:00`;
      await api.createCajaMov(payload);
      setF({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' }); await load(dia);
    } catch (e) { setErr(e.message); }
  };
  const borrar = async (m) => {
    if (!confirm(`Borrar "${m.descripcion}"?`)) return;
    try { await api.deleteCajaMov(m.id); await load(dia); } catch (e) { setErr(e.message); }
  };
  const fmt = (n) => '$' + (+(n || 0)).toLocaleString('es-AR', { minimumFractionDigits: 2 });
  const hora = (iso) => { try { return formatApiTime(iso); } catch { return '—'; } };
  const movs = res?.movimientos || [];
  const ordenados = [...movs].sort((a, b) => parseApiUtc(b.fecha) - parseApiUtc(a.fecha));
  const entradas = movs.filter(m => m.tipo === 'ENTRADA');
  const salidas = movs.filter(m => m.tipo === 'SALIDA');
  const balance = res?.balance || 0;
  const porMedio = res?.por_medio || {};
  const mediosConMov = [...MEDIOS_SEL.map(([v]) => v), 'tarjeta'].filter(v => ((porMedio[v]?.entrada || 0) > 0 || (porMedio[v]?.salida || 0) > 0));
  const ventasN = movs.filter(m => m.tipo === 'ENTRADA' && m.pedido_id && !String(m.descripcion || '').startsWith('Anulación')).length;
  const ticketProm = ventasN > 0 ? movs.filter(m => m.tipo === 'ENTRADA' && m.pedido_id).reduce((a, m) => a + (+m.monto || 0), 0) / ventasN : 0;
  const origenDe = (m) => {
    if (m.pedido_id) return String(m.descripcion || '').startsWith('Anulación') ? `anul. venta #${m.pedido_id}` : `venta #${m.pedido_id}`;
    if (m.compra_id) return `compra #${m.compra_id}`;
    return m.automatico ? 'auto' : 'manual';
  };
  return <section>
    <div className="sec-head"><h2>{dia === hoy ? 'Historial' : `Historial · ${dia}`}</h2>{dia !== hoy
      && <button className="fab" onClick={() => { setDia(hoy); load(hoy); }}>‹ Volver a hoy</button>}</div>
    <Err e={err} />
    <div className="row day-picker">
      <button className="ghost" onClick={() => mover(-1)}>‹ Ayer</button>
      <input type="date" value={dia} max={hoy} onChange={e => setDiaLoad(e.target.value)} />
      <button className="ghost" onClick={() => mover(1)} disabled={!dia || dia >= hoy}>Mañana ›</button>
    </div>
    <div className="cards">
      <div className="card"><span>Entrada</span><b className="in">{loading ? '…' : fmt(res?.total_entrada || 0)}</b><small>{entradas.length} movimientos{ventasN > 0 ? ` · ${ventasN} ventas · ticket ${fmt(ticketProm)}` : ''}</small></div>
      <div className="card"><span>Salida</span><b className="out">{loading ? '…' : fmt(res?.total_salida || 0)}</b><small>{salidas.length} movimientos</small></div>
      <div className="card"><span>Balance</span><b className={balance < 0 ? 'out' : balance > 0 ? 'in' : ''}>{loading ? '…' : fmt(balance)}</b><small>entrada − salida</small></div>
    </div>
    {mediosConMov.length > 0 && <div className="ped-badges" style={{ margin: '4px 0 8px' }}>
      {mediosConMov.map(v => {
        const e = porMedio[v]?.entrada || 0, s = porMedio[v]?.salida || 0;
        const t = (e > 0 && s > 0) ? `+${fmt(e)} / −${fmt(s)}` : e > 0 ? `+${fmt(e)}` : `−${fmt(s)}`;
        return <span key={v} className="badge ok">{MEDIO_SHORT[v] || v} · {t}</span>;
      })}
    </div>}
    <div className="sale-box">
      <h3>Movimiento manual (gastos, entradas extra)</h3>
      <p className="muted small">Las ventas y los pagos a distribuidoras se registran solos. {dia !== hoy ? `Se cargará en ${dia} (día visible).` : 'Se cargará hoy.'}</p>
      <div className="row">
        <Field label="Tipo"><select value={f.tipo} onChange={e => setF({ ...f, tipo: e.target.value })}><option value="SALIDA">salida</option><option value="ENTRADA">entrada</option></select></Field>
        <Field label="Medio"><select value={f.medio} onChange={e => setF({ ...f, medio: e.target.value })}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></Field>
        <Field label="Descripción"><input placeholder="Ej: Cabify" value={f.descripcion} onChange={e => setF({ ...f, descripcion: e.target.value })} /></Field>
        <Field label="Monto"><input type="number" min="0" step="0.01" placeholder="0" value={f.monto} onChange={e => setF({ ...f, monto: e.target.value })} /></Field>
        <button onClick={guardar}>Agregar</button>
      </div>
    </div>
    <h3>Movimientos {movs.length > 0 && <span className="muted">· {movs.length}</span>}</h3>
    {loading ? <p className="muted">Cargando…</p> : ordenados.length === 0
      ? <p className="muted">Sin movimientos este día. {dia === hoy ? 'Registrá la primera venta en Principal o cargá un gasto arriba.' : 'Probá con otro día o cargá un movimiento manual.'}</p>
      : <div className="tbl-wrap"><table><thead><tr><th>Hora</th><th>Detalle</th><th>Medio</th><th>Entrada</th><th>Salida</th><th>Origen</th><th></th></tr></thead>
        <tbody>{ordenados.map(m => <tr key={m.id}>
          <td>{hora(m.fecha)}</td>
          <td>{m.descripcion}</td>
          <td><span className="badge ok">{MEDIO_SHORT[m.medio] || m.medio}</span></td>
          <td>{m.tipo === 'ENTRADA' ? <b className="in">{fmt(m.monto)}</b> : '—'}</td>
          <td>{m.tipo === 'SALIDA' ? <b className="out">{fmt(m.monto)}</b> : '—'}</td>
          <td><span className={m.automatico ? 'badge ok' : 'sin-cat'}>{origenDe(m)}</span></td>
          <td>{!m.automatico && <button onClick={() => borrar(m)}>borrar</button>}</td>
        </tr>)}
        </tbody></table></div>}
  </section>;
}

/* ---------- Hoy eliminado: su contenido vive en Principal (Ventas + Caja) ---------- */

export default Caja;
