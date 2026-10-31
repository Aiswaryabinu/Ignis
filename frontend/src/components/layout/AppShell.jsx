import {
  BarChart3,
  Bell,
  Boxes,
  BriefcaseBusiness,
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
    { label: 'Subscription Plans', href: '/plans', icon: Layers3 },
    { label: 'Quotations', href: '/quotations', icon: FileText },
    { label: 'Subscriptions', href: '/subscriptions', icon: BriefcaseBusiness },
    { label: 'Invoices', href: '/invoices', icon: ReceiptText },
    { label: 'Discounts', href: '/discounts', icon: Tag },
    { label: 'Payments', href: '/payments', icon: CreditCard },
    { label: 'Reports', href: '/reports', icon: BarChart3 },
    { label: 'Overview', href: '/dashboard', icon: Grid2x2 },
    { label: 'Settings', href: '/settings', icon: Settings },
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
            <div className="user-select">Admin</div>
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

        <div className={`content-panel ${activeNav.toLowerCase()}-content`}>
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
