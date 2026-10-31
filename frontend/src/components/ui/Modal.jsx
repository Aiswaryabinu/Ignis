export function Modal({ title, children, isOpen = false }) {
  if (!isOpen) return null;

  return (
    <div role="dialog" aria-modal="true">
      <h3>{title}</h3>
      {children}
    </div>
  );
}
