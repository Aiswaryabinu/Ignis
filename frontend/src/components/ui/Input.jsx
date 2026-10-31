export function Input({ label, ...props }) {
  return (
    <label>
      {label && <span>{label}</span>}
      <input {...props} />
    </label>
  );
}
