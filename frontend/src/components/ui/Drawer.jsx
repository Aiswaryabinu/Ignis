export function Drawer({ title, children, isOpen = false }) {
  if (!isOpen) return null;

  return (
    <aside>
      <h3>{title}</h3>
      {children}
    </aside>
  );
}
