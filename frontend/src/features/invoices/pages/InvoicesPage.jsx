import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { InvoiceTable } from '../components/InvoiceTable.jsx';

const invoices = [
  { id: 'INV-1052', invoiceNumber: 'INV-1052', customer: 'Kerala Foods Co.', subscription: 'SUB-0002', date: '31 Oct 2026', due: '15 Nov 2026', total: 254880, status: 'Draft' },
  { id: 'INV-1051', invoiceNumber: 'INV-1051', customer: 'Northwind Traders', subscription: 'SUB-0001', date: '31 Oct 2026', due: '15 Nov 2026', total: 109150, status: 'Draft' },
  { id: 'INV-1042', invoiceNumber: 'INV-1042', customer: 'Northwind Traders', subscription: 'SUB-0001', date: '01 Oct 2026', due: '16 Oct 2026', total: 109150, status: 'Overdue' },
  { id: 'INV-1043', invoiceNumber: 'INV-1043', customer: 'Kerala Foods Co.', subscription: 'SUB-0002', date: '15 Oct 2026', due: '14 Nov 2026', total: 254880, status: 'Confirmed' },
  { id: 'INV-1044', invoiceNumber: 'INV-1044', customer: 'Tidewater Logistics', subscription: 'SUB-0003', date: '01 Oct 2026', due: '01 Oct 2026', total: 8850, status: 'Paid' },
  { id: 'INV-1041', invoiceNumber: 'INV-1041', customer: 'Northwind Traders', subscription: 'SUB-0001', date: '01 Sep 2026', due: '16 Sep 2026', total: 109150, status: 'Paid' },
  { id: 'INV-1045', invoiceNumber: 'INV-1045', customer: 'Kerala Foods Co.', subscription: 'SUB-0002', date: '31 Oct 2026', due: '30 Nov 2026', total: 0, status: 'Draft' },
];

export function InvoicesPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const filteredInvoices = useMemo(() => invoices.filter((invoice) => {
    const matchesQuery = [invoice.invoiceNumber, invoice.customer, invoice.subscription]
      .some((value) => value.toLowerCase().includes(query.toLowerCase()));
    return matchesQuery && (status === 'All statuses' || invoice.status === status);
  }), [query, status]);

  return (
    <AppShell
      title="Invoices"
      description="Created from subscriptions. Never billed twice."
      breadcrumb="Brightloop / Invoices"
      activeNav="invoices"
      primaryAction={<button className="primary-action" type="button">Generate invoices</button>}
      secondaryAction={<button className="secondary-action" type="button">Export</button>}
    >
      <div className="invoice-toolbar">
        <input
          className="invoice-search"
          type="search"
          placeholder="Search invoices..."
          aria-label="Search invoices"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select
          className="invoice-filter"
          aria-label="Filter invoices by status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option>All statuses</option>
          <option>Draft</option>
          <option>Overdue</option>
          <option>Confirmed</option>
          <option>Paid</option>
        </select>
      </div>

      <div className="data-card invoice-card">
        <InvoiceTable rows={filteredInvoices} />
        <div className="table-footer">Showing {filteredInvoices.length} of {invoices.length} records</div>
      </div>
    </AppShell>
  );
}
