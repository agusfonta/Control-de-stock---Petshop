import { useState } from 'react';
import { api, setSession } from '../../api';

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

export default Login;
