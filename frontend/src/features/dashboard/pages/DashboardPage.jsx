import { AppShell } from '../../../components/layout/AppShell.jsx';

const chartData = [
  { month: 'Jun', billed: 210, collected: 180 },
  { month: 'Jul', billed: 240, collected: 220 },
  { month: 'Aug', billed: 228, collected: 210 },
  { month: 'Sep', billed: 262, collected: 245 },
  { month: 'Oct', billed: 300, collected: 280 },
];

export function DashboardPage() {
  return (
    <AppShell title="Overview" description="Recurring revenue at a glance." breadcrumb="Brightloop / Overview" activeNav="overview">
      <p className="overview-intro">Snapshot for 31 Oct 2026. Revenue is what customers have paid. Outstanding is what has been invoiced but not yet paid.</p>
      <div className="metric-grid overview-metrics">
        <div className="metric-card"><span>Active subscriptions</span><strong>2</strong><small>1 confirmed, starting soon</small></div>
        <div className="metric-card"><span>Monthly recurring revenue</span><strong className="success-value">₹1,10,500</strong><small>Weekly and yearly plans normalised to a month</small></div>
        <div className="metric-card"><span>Collected</span><strong>₹2,18,000</strong><small>3 payments recorded</small></div>
        <div className="metric-card"><span>Outstanding</span><strong>₹2,64,030</strong><small>Invoiced but not yet paid</small></div>
        <div className="metric-card danger-metric"><span>Overdue invoices</span><strong>1</strong><small>₹1,09,150 to chase</small></div>
      </div>
      <div className="overview-grid">
        <section className="dashboard-card chart-card"><h2>Billed vs collected</h2><p>Last five months, in ₹ thousand</p><div className="chart-legend"><span><i className="legend-billed" /> Billed</span><span><i className="legend-collected" /> Collected</span></div><div className="bar-chart">{chartData.map((item) => <div className="bar-group" key={item.month}><div className="bars"><i style={{ height: `${item.billed / 2.2}px` }} /><i style={{ height: `${item.collected / 2.2}px` }} /></div><span>{item.month}</span><b>{item.billed}k</b></div>)}</div></section>
        <section className="dashboard-card chase-card"><h2>Needs chasing</h2><p>Overdue invoices, oldest first</p><div className="chase-row"><div><strong>INV-1042</strong><span>Northwind Traders, 15 days overdue</span></div><b>₹1,09,150</b></div></section>
      </div>
      <div className="overview-grid overview-lower-grid">
        <section className="dashboard-card pipeline-card"><h2>Subscription pipeline</h2><p>Where all 5 subscriptions stand</p>{[['Draft', 0], ['Quotation', 1], ['Confirmed', 1], ['Active', 2], ['Closed', 1]].map(([label, count]) => <div className="pipeline-row" key={label}><div><span>{label}</span><b>{count}</b></div><i><em style={{ width: `${count * 20}%` }} /></i></div>)}</section>
        <section className="dashboard-card health-card"><h2>Invoice health</h2><p>Count and value by stage</p>{[['Paid', '₹1,18,000', 'success'], ['Awaiting payment', '₹2,54,880', 'info'], ['Overdue', '₹1,09,150', 'danger'], ['Draft, not sent', '₹3,64,030', 'warning']].map(([label, value, tone]) => <div className="health-row" key={label}><span className={`status-pill ${tone}`}><span className="dot" />{label}</span><b>{value}</b></div>)}</section>
        <section className="dashboard-card expiry-card"><h2>Upcoming expiries</h2><p>Active subscriptions that will need renewing</p><div className="expiry-row"><strong>Northwind Traders</strong><b>₹92,500</b><span>Business Monthly, expires 31 May 2027</span></div><div className="expiry-row"><strong>Kerala Foods Co.</strong><b>₹2,16,000</b><span>Scale Annual, expires 14 Mar 2027</span></div></section>
      </div>
      <section className="dashboard-card recent-card"><h2>Recent payments</h2><p>Latest money in, matched to invoices</p><table className="data-table"><thead><tr><th>Reference</th><th>Invoice</th><th>Method</th><th className="amount-column">Amount</th><th>Date</th></tr></thead><tbody><tr><td className="table-link">PAY-501</td><td>INV-1044</td><td>UPI</td><td className="amount-column">₹8,850</td><td>03 Oct 2026</td></tr><tr><td className="table-link">PAY-500</td><td>INV-1041</td><td>Bank transfer</td><td className="amount-column">₹1,09,150</td><td>12 Sep 2026</td></tr><tr><td className="table-link">PAY-499</td><td>INV-1043</td><td>Card</td><td className="amount-column">₹1,00,000</td><td>20 Oct 2026</td></tr></tbody></table></section>
    </AppShell>
  );
}
