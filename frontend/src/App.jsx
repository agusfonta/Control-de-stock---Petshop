import { useEffect, useState } from 'react';
import { api, getSession, setSession } from './api';
import Modal from './components/Modal';
import Login from './features/auth/Login';
import Proveedores from './features/proveedores/Proveedores';
import Productos from './features/productos/Productos';
import Ventas from './features/ventas/Ventas';
import Clientes from './features/clientes/Clientes';
import Caja from './features/caja/Caja';

const TABS = ['Principal', 'Stock', 'Clientes', 'Distribuidoras', 'Historial'];

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
