function Field({ label, hint, error, className, children }) {
  return <label className={'field' + (className ? ' ' + className : '')}><span>{label}{hint && <small> — {hint}</small>}</span>{children}{error && <small className="field-err">{error}</small>}</label>;
}


export default Field;
