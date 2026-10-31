export function Toast({ message, type = 'info' }) {
  return <div className={`toast toast-${type}`}>{message}</div>;
}
