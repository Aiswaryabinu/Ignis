export function Select({ label, options = [], ...props }) {
  return (
    <label>
      {label && <span>{label}</span>}
      <select {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
