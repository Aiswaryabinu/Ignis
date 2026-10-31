import {
  BarChart3,
  Bell,
  Boxes,
  BriefcaseBusiness,
  ChevronDown,
  CreditCard,
  FileText,
  Grid2x2,
  Layers3,
  LogOut,
  ReceiptText,
  Search,
  Settings,
  Tag,
  Users,
  WalletCards,
} from 'lucide-react';

export function AppShell({
  title,
  description,
  breadcrumb = 'Brightloop',
  primaryAction,
  secondaryAction,
  children,
  activeNav = 'customers',
}) {
  const navItems = [
    { label: 'Customers', href: '/customers', icon: Users },
    { label: 'Products', href: '/products', icon: Boxes },
    { label: 'Subscription Plans', href: '#', icon: Layers3 },
    { label: 'Quotations', href: '#', icon: FileText },
    { label: 'Subscriptions', href: '#', icon: BriefcaseBusiness },
    { label: 'Invoices', href: '#', icon: ReceiptText },
    { label: 'Discounts', href: '#', icon: Tag },
    { label: 'Payments', href: '#', icon: CreditCard },
    { label: 'Reports', href: '#', icon: BarChart3 },
    { label: 'Overview', href: '#', icon: Grid2x2 },
    { label: 'Settings', href: '#', icon: Settings },
  ];

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-row">
          <div className="brand-badge small">B</div>
          <div className="brand-word">brightloop</div>
        </div>

        <div className="nav-section">
          <div className="nav-label">WORKSPACE</div>
          <nav className="sidebar-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const selected = item.label.toLowerCase() === activeNav.toLowerCase();
              return (
                <a
                  key={item.label}
                  href={item.href}
                  className={`nav-item ${selected ? 'active' : ''}`}
                >
                  <span className="nav-icon"><Icon size={17} strokeWidth={2.15} /></span>
                  <span>{item.label}</span>
                  {item.label === 'Invoices' && <span className="nav-badge">2</span>}
                </a>
              );
            })}
          </nav>
        </div>

        <div className="sidebar-footer">
          <a href="#" className="nav-item signout">
            <span className="nav-icon"><LogOut size={17} strokeWidth={2.15} /></span>
            <span>Sign out</span>
          </a>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            <span>{breadcrumb}</span>
          </div>

          <div className="topbar-controls">
            <div className="user-select">
              <span>Admin</span>
              <ChevronDown size={16} strokeWidth={2.2} />
            </div>
            <div className="notification-wrap">
              <Bell size={16} strokeWidth={2.2} />
              <span className="notification-pill" />
            </div>
            <div className="avatar-block">
              <div className="avatar-circle">AK</div>
              <div className="avatar-meta">
                <div className="avatar-name">Aisha Khan</div>
                <div className="avatar-role">Admin</div>
              </div>
            </div>
          </div>
        </header>

        <div className="content-panel">
          <div className="page-header-row">
            <div>
              <h1 className="page-title">{title}</h1>
              {description && <p className="page-description">{description}</p>}
            </div>

            <div className="page-actions">
              {secondaryAction}
              {primaryAction}
            </div>
          </div>

          {children}
        </div>
      </main>
    </div>
  );
}
