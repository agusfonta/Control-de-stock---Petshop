import { useEffect, useState } from 'react';

function useLoad(fn, deps = []) {
  const [data, setData] = useState(null); const [err, setErr] = useState(''); const [loading, setLoading] = useState(true);
  const reload = async () => {
    setLoading(true); setErr('');
    try { setData(await fn()); } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, deps);
  return { data, err, loading, reload };
}

export default useLoad;
