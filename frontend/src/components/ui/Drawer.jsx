export function Drawer({ title, children, isOpen = false, onClose, className = '' }) {
  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose?.();
    }}>
      <aside className={`side-drawer ${className}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer-header">
          <h2>{title}</h2>
          <button className="drawer-close" type="button" onClick={onClose}>Close</button>
        </div>
        {children}
      </aside>
    </div>
  );
}
