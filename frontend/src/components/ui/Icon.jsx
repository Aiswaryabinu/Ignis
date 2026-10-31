export function Icon({ name, children }) {
  return <span aria-label={name}>{children || name}</span>;
}
