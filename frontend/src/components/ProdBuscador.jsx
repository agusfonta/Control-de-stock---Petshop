import { useEffect, useState } from 'react';

function ProdBuscador({ prods, value, onChange, allowSinStock = false }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const norm = s => (s || '').toLowerCase();

  useEffect(() => {
    if (!value) { setQuery(''); return; }
    const p = prods.find(x => String(x.id) === String(value));
    if (p) setQuery(p.nombre);
  }, [value, prods]);

  const sugs = query.trim().length > 0
    ? prods.filter(p => p.activo && (norm(p.nombre).includes(norm(query)) || norm(p.marca || '').includes(norm(query))))
    : [];

  return (
    <div className="autocomplete-wrap">
      <input
        placeholder="Buscar producto..."
        value={query}
        autoComplete="off"
        onChange={e => { setQuery(e.target.value); onChange(''); setOpen(true); }}
        onFocus={() => { if (query.trim()) setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && sugs.length > 0 && (
        <ul className="sug-list">
          {sugs.map(p => (
            <li
              key={p.id}
              className={'sug-item' + (!allowSinStock && p.stock === 0 ? ' disabled' : '')}
              onMouseDown={(allowSinStock || p.stock > 0) ? () => { onChange(p.id); setQuery(p.nombre); setOpen(false); } : e => e.preventDefault()}
            >
              <span>{p.nombre}{p.marca ? ` · ${p.marca}` : ''}</span>
              {p.stock === 0
                ? <span className="badge out">Sin stock</span>
                : <span className="badge ok">stock: {p.stock}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


export default ProdBuscador;
