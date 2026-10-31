import { BarChart3, Bell, Boxes, BriefcaseBusiness, CreditCard, FileText, Grid2x2, Layers3, LogOut, ReceiptText, Settings, Tag, Users } from 'lucide-react';
import { useAuth } from '../../app/providers.jsx';

export function AppShell({
  title,
  description,
  breadcrumb = 'Brightloop',
  primaryAction,
  secondaryAction,
  children,
  activeNav = 'customers',
}) {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const isCustomer = user?.role === 'CUSTOMER';
  const navItems = isCustomer
    ? [
      { label: 'Dashboard', href: '/customer-dashboard', icon: Grid2x2 },
      { label: 'My Subscriptions', href: '/subscriptions', icon: BriefcaseBusiness },
      { label: 'My Invoices', href: '/invoices', icon: ReceiptText },
      { label: 'Payment History', href: '/payments', icon: CreditCard },
      { label: 'My Profile', href: '/settings', icon: Settings },
    ]
    : isAdmin
      ? [
        { label: 'Dashboard', href: '/dashboard', icon: Grid2x2 },
        { label: 'Customers', href: '/customers', icon: Users },
        { label: 'Staff & Users', href: '/staff-users', icon: Users },
        { label: 'Products', href: '/products', icon: Boxes },
        { label: 'Plans', href: '/plans', icon: Layers3 },
        { label: 'Quotations', href: '/quotations', icon: FileText },
        { label: 'Subscriptions', href: '/subscriptions', icon: BriefcaseBusiness },
        { label: 'Invoices', href: '/invoices', icon: ReceiptText },
        { label: 'Payments', href: '/payments', icon: CreditCard },
        { label: 'Discounts', href: '/discounts', icon: Tag },
        { label: 'Taxes', href: '/taxes', icon: Tag },
        { label: 'Reports', href: '/reports', icon: BarChart3 },
        { label: 'Settings', href: '/settings', icon: Settings },
      ]
      : [
        { label: 'Dashboard', href: '/dashboard', icon: Grid2x2 },
        { label: 'Customers', href: '/customers', icon: Users },
        { label: 'Quotations', href: '/quotations', icon: FileText },
        { label: 'Subscriptions', href: '/subscriptions', icon: BriefcaseBusiness },
        { label: 'Invoices', href: '/invoices', icon: ReceiptText },
        { label: 'Payments', href: '/payments', icon: CreditCard },
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
              const selected = item.href === window.location.pathname || item.label.toLowerCase() === activeNav.toLowerCase();
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
          <button type="button" className="nav-item signout" onClick={logout}>
            <span className="nav-icon"><LogOut size={17} strokeWidth={2.15} /></span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            <span>{breadcrumb}</span>
          </div>

          <div className="topbar-controls">
            <div className="user-select">{user?.role || 'User'}</div>
            <div className="notification-wrap">
              <Bell size={16} strokeWidth={2.2} />
              <span className="notification-pill" />
            </div>
            <div className="avatar-block">
              <div className="avatar-circle">{(user?.full_name || user?.email || 'U').slice(0, 2).toUpperCase()}</div>
              <div className="avatar-meta">
                <div className="avatar-name">{user?.full_name || user?.email}</div>
                <div className="avatar-role">{user?.role}</div>
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
              {!isCustomer && secondaryAction}
              {!isCustomer && primaryAction}
            </div>
          </div>

          {children}
        </div>
      </main>
    </div>
  );
}
