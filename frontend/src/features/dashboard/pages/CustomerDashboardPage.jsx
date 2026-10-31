import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient.js';

export function CustomerDashboardPage() {
  const subscriptions = useQuery({
    queryKey: ['subscriptions', 'customer-dashboard'],
    queryFn: async () => (await apiClient.get('/subscriptions')).data,
  });
  const invoices = useQuery({
    queryKey: ['invoices', 'customer-dashboard'],
    queryFn: async () => (await apiClient.get('/invoices')).data,
  });
  const activeSubscriptions = (subscriptions.data || []).filter((item) => ['Active', 'Confirmed'].includes(item.status));
  const outstanding = (invoices.data || []).reduce((total, invoice) => total + (invoice.balance || 0), 0);

  return (
    <AppShell title="Dashboard" description="Your subscription account at a glance." breadcrumb="Brightloop / Dashboard" activeNav="dashboard">
      <div className="metric-grid overview-metrics">
        <div className="metric-card"><span>Active subscriptions</span><strong>{activeSubscriptions.length}</strong><small>Current plans and renewals</small></div>
        <div className="metric-card"><span>Invoices</span><strong>{(invoices.data || []).length}</strong><small>Your billing history</small></div>
        <div className="metric-card"><span>Outstanding</span><strong>₹{outstanding.toLocaleString('en-IN')}</strong><small>Balance currently due</small></div>
      </div>
      <section className="dashboard-card">
        <h2>Next steps</h2>
        <p>Review your subscriptions, download invoices, or view payment history from the sidebar.</p>
      </section>
    </AppShell>
  );
}
