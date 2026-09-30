import { useEffect, useState } from 'react';
import { api } from '../../api';
import Err from '../../components/Err';
import Field from '../../components/Field';
import { MEDIOS_SEL, MEDIO_SHORT } from '../../constants/paymentMethods';
import { todayLocal, shiftLocalDay, formatApiTime, formatApiDate, parseApiUtc } from '../../utils/dates';

function Caja() {
  const hoy = todayLocal();
  const [dia, setDia] = useState(hoy);
  const [res, setRes] = useState(null);
  const [mensual, setMensual] = useState(null);
  const [modo, setModo] = useState('dia');
  const [mes, setMes] = useState(hoy.slice(0, 7));
  const [filtroTipo, setFiltroTipo] = useState('');
  const [filtroProveedor, setFiltroProveedor] = useState('');
  const [filtroCliente, setFiltroCliente] = useState('');
  const [clientes, setClientes] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' });
  const fmt = n => '$' + (+(n || 0)).toLocaleString('es-AR', { minimumFractionDigits: 2 });

  const loadDia = async d => {
    setErr(''); setLoading(true);
    try { setRes(await api.caja(d)); } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  const loadMes = async m => {
    setErr(''); setLoading(true);
    try {
      setMensual(await api.cajaMensual({
        mes: m,
        tipo: filtroTipo,
        proveedor_id: filtroProveedor,
        cliente_id: filtroCliente,
      }));
    } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { if (modo === 'dia') loadDia(dia); }, [dia, modo]);
  useEffect(() => {
    if (modo !== 'mes') return;
    loadMes(mes);
  }, [mes, modo, filtroTipo, filtroProveedor, filtroCliente]);
  useEffect(() => {
    const cargarFiltros = async () => {
      try {
        const [clientesData, proveedoresData] = await Promise.all([api.clientes(), api.proveedores()]);
        setClientes(clientesData || []);
        setProveedores(proveedoresData || []);
      } catch (e) { setErr(e.message); }
    };
    cargarFiltros();
  }, []);

  const mover = d => setDia(shiftLocalDay(dia, d));
  const setDiaLoad = v => { if (v) setDia(v > hoy ? hoy : v); };
  const guardar = async () => {
    if (f.descripcion.trim().length < 2 || !(+f.monto > 0)) { setErr('Descripción (mín 2) y monto mayor a 0'); return; }
    try {
      const payload = { tipo: f.tipo, medio: f.medio, descripcion: f.descripcion.trim(), monto: +f.monto };
      if (dia !== hoy) payload.fecha = `${dia}T12:00:00`;
      await api.createCajaMov(payload); setF({ tipo: 'SALIDA', medio: 'efectivo', descripcion: '', monto: '' }); await loadDia(dia);
    } catch (e) { setErr(e.message); }
  };
  const borrar = async m => {
    if (!confirm(`Borrar "${m.descripcion}"?`)) return;
    try { await api.deleteCajaMov(m.id); await loadDia(dia); } catch (e) { setErr(e.message); }
  };

  const movs = res?.movimientos || [];
  const ordenados = [...movs].sort((a, b) => parseApiUtc(b.fecha) - parseApiUtc(a.fecha));
  const entradas = movs.filter(m => m.tipo === 'ENTRADA');
  const salidas = movs.filter(m => m.tipo === 'SALIDA');
  const mediosConMov = MEDIOS_SEL.map(([v]) => v).filter(v => ((res?.por_medio?.[v]?.entrada || 0) > 0 || (res?.por_medio?.[v]?.salida || 0) > 0));
  const ventasN = movs.filter(m => m.tipo === 'ENTRADA' && m.pedido_id && !String(m.descripcion || '').startsWith('Anulación')).length;
  const ticketProm = ventasN ? movs.filter(m => m.tipo === 'ENTRADA' && m.pedido_id).reduce((a, m) => a + (+m.monto || 0), 0) / ventasN : 0;
  const origenDe = m => m.pedido_id ? (String(m.descripcion || '').startsWith('Anulación') ? `anul. venta #${m.pedido_id}` : `venta #${m.pedido_id}`) : m.compra_id ? `compra #${m.compra_id}` : (m.automatico ? 'auto' : 'manual');

  return <section>
    <div className="sec-head"><h2>Historial</h2></div>
    <Err e={err} />
    <div className="row day-picker"><button className={modo === 'dia' ? '' : 'ghost'} onClick={() => setModo('dia')}>Día</button><button className={modo === 'mes' ? '' : 'ghost'} onClick={() => setModo('mes')}>Mes</button>{modo === 'dia' ? <><button className="ghost" onClick={() => mover(-1)}>‹ Ayer</button><input type="date" value={dia} max={hoy} onChange={e => setDiaLoad(e.target.value)} /><button className="ghost" onClick={() => mover(1)} disabled={dia >= hoy}>Mañana ›</button></> : <input type="month" value={mes} onChange={e => setMes(e.target.value)} />}</div>

    {modo === 'dia' ? <>
      <div className="cards">
        <div className="card"><span>Entrada</span><b className="in">{loading ? '…' : fmt(res?.total_entrada)}</b><small>{entradas.length} movimientos{ventasN ? ` · ${ventasN} ventas · ticket ${fmt(ticketProm)}` : ''}</small></div>
        <div className="card"><span>Salida</span><b className="out">{loading ? '…' : fmt(res?.total_salida)}</b><small>{salidas.length} movimientos</small></div>
        <div className="card"><span>Balance</span><b className={(res?.balance || 0) < 0 ? 'out' : (res?.balance || 0) > 0 ? 'in' : ''}>{loading ? '…' : fmt(res?.balance)}</b><small>entrada − salida</small></div>
      </div>
      {mediosConMov.length > 0 && <div className="ped-badges" style={{ margin: '4px 0 8px' }}>{mediosConMov.map(v => { const x = res?.por_medio?.[v] || {}; const e = x.entrada || 0, s = x.salida || 0; return <span key={v} className="badge ok">{MEDIO_SHORT[v] || v} · {e > 0 ? `+${fmt(e)}` : ''}{e > 0 && s > 0 ? ' / ' : ''}{s > 0 ? `−${fmt(s)}` : ''}</span>; })}</div>}
      <div className="sale-box"><h3>Movimiento manual</h3><p className="muted small">Las ventas y pagos a distribuidoras se registran solos. {dia !== hoy ? `Se cargará en ${dia}.` : 'Se cargará hoy.'}</p><div className="row"><Field label="Tipo"><select value={f.tipo} onChange={e => setF({ ...f, tipo: e.target.value })}><option value="SALIDA">salida</option><option value="ENTRADA">entrada</option></select></Field><Field label="Medio"><select value={f.medio} onChange={e => setF({ ...f, medio: e.target.value })}>{MEDIOS_SEL.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></Field><Field label="Descripción"><input placeholder="Ej: Cabify" value={f.descripcion} onChange={e => setF({ ...f, descripcion: e.target.value })} /></Field><Field label="Monto"><input type="number" min="0" step="0.01" value={f.monto} onChange={e => setF({ ...f, monto: e.target.value })} /></Field><button onClick={guardar}>Agregar</button></div></div>
      <h3>Movimientos {movs.length > 0 && <span className="muted">· {movs.length}</span>}</h3>
      {loading ? <p className="muted">Cargando…</p> : ordenados.length === 0 ? <p className="muted">Sin movimientos este día.</p> : <div className="tbl-wrap"><table><thead><tr><th>Hora</th><th>Detalle</th><th>Medio</th><th>Entrada</th><th>Salida</th><th>Origen</th><th></th></tr></thead><tbody>{ordenados.map(m => <tr key={m.id}><td>{formatApiTime(m.fecha)}</td><td>{m.descripcion}</td><td><span className="badge ok">{MEDIO_SHORT[m.medio] || m.medio}</span></td><td>{m.tipo === 'ENTRADA' ? <b className="in">{fmt(m.monto)}</b> : '—'}</td><td>{m.tipo === 'SALIDA' ? <b className="out">{fmt(m.monto)}</b> : '—'}</td><td><span className={m.automatico ? 'badge ok' : 'sin-cat'}>{origenDe(m)}</span></td><td>{!m.automatico && <button onClick={() => borrar(m)}>borrar</button>}</td></tr>)}</tbody></table></div>}
    </> : <>
      <div className="row history-filters">
        <Field label="Mostrar">
          <select value={filtroTipo} onChange={e => setFiltroTipo(e.target.value)}>
            <option value="">Entradas y salidas</option>
            <option value="ENTRADA">Solo entradas</option>
            <option value="SALIDA">Solo salidas</option>
          </select>
        </Field>
        <Field label="Distribuidora">
          <select value={filtroProveedor} onChange={e => setFiltroProveedor(e.target.value)}>
            <option value="">Todas</option>
            {proveedores.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </Field>
        <Field label="Cliente">
          <select value={filtroCliente} onChange={e => setFiltroCliente(e.target.value)}>
            <option value="">Todos</option>
            {clientes.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </Field>
      </div>
      <div className="cards"><div className="card"><span>Entrada del mes</span><b className="in">{loading ? '…' : fmt(mensual?.total_entrada)}</b><small>Según filtros aplicados</small></div><div className="card"><span>Salida del mes</span><b className="out">{loading ? '…' : fmt(mensual?.total_salida)}</b><small>Según filtros aplicados</small></div><div className="card"><span>Balance del mes</span><b className={(mensual?.balance || 0) < 0 ? 'out' : (mensual?.balance || 0) > 0 ? 'in' : ''}>{loading ? '…' : fmt(mensual?.balance)}</b><small>entrada − salida</small></div></div>
      {loading ? <p className="muted">Cargando…</p> : (mensual?.movimientos || []).length === 0 ? <p className="muted">Sin movimientos para este filtro.</p> : <div className="tbl-wrap"><table><thead><tr><th>Fecha</th><th>Hora</th><th>Detalle</th><th>Medio</th><th>Entrada</th><th>Salida</th><th>Origen</th></tr></thead><tbody>{mensual.movimientos.map(m => {
        const origen = m.pedido_id
          ? `venta #${m.pedido_id}${m.cliente_nombre ? ` · ${m.cliente_nombre}` : ''}`
          : m.compra_id
            ? `compra #${m.compra_id}${m.proveedor_nombre ? ` · ${m.proveedor_nombre}` : ''}`
            : (m.automatico ? 'auto' : 'manual');
        return <tr key={m.id}><td>{formatApiDate(m.fecha)}</td><td>{formatApiTime(m.fecha)}</td><td>{m.descripcion}</td><td><span className="badge ok">{MEDIO_SHORT[m.medio] || m.medio}</span></td><td>{m.tipo === 'ENTRADA' ? <b className="in">{fmt(m.monto)}</b> : '—'}</td><td>{m.tipo === 'SALIDA' ? <b className="out">{fmt(m.monto)}</b> : '—'}</td><td><span className={m.automatico ? 'badge ok' : 'sin-cat'}>{origen}</span></td></tr>;
      })}</tbody></table></div>}
    </>}
  </section>;
}

export default Caja;
