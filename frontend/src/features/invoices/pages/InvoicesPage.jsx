import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';
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

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export function InvoicesPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [notice, setNotice] = useState('');
  const filteredInvoices = useMemo(() => invoices.filter((invoice) => {
    const matchesQuery = [invoice.invoiceNumber, invoice.customer, invoice.subscription]
      .some((value) => value.toLowerCase().includes(query.toLowerCase()));
    return matchesQuery && (status === 'All statuses' || invoice.status === status);
  }), [query, status]);

  const generateInvoices = () => {
    setNotice('Nothing new to bill. Every active subscription is already invoiced.');
    window.setTimeout(() => setNotice(''), 3500);
  };

  return (
    <AppShell
      title="Invoices"
      description="Created from subscriptions. Never billed twice."
      breadcrumb="Brightloop / Invoices"
      activeNav="invoices"
      primaryAction={<button className="primary-action" type="button" onClick={generateInvoices}>Generate invoices</button>}
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
        <InvoiceTable rows={filteredInvoices} onSelect={setSelectedInvoice} />
        <div className="table-footer">Showing {filteredInvoices.length} of {invoices.length} records</div>
      </div>

      {notice && <div className="invoice-notice" role="status">{notice}</div>}

      <Drawer
        title={selectedInvoice?.invoiceNumber || 'Invoice'}
        isOpen={Boolean(selectedInvoice)}
        onClose={() => setSelectedInvoice(null)}
        className="invoice-detail-drawer"
      >
        {selectedInvoice && (
          <>
            <span className={`status-pill ${selectedInvoice.status === 'Paid' ? 'success' : selectedInvoice.status === 'Overdue' ? 'danger' : selectedInvoice.status === 'Confirmed' ? 'info' : 'warning'}`}>
              <span className="dot" />
              {selectedInvoice.status}
            </span>
            <div className="invoice-status-tabs">
              {['Draft', 'Confirmed', 'Paid'].map((option) => (
                <button key={option} type="button" className={selectedInvoice.status === option ? 'selected' : ''}>{option}</button>
              ))}
            </div>
            <dl className="invoice-detail-list">
              <div><dt>Invoice</dt><dd>{selectedInvoice.invoiceNumber}</dd></div>
              <div><dt>Customer</dt><dd>{selectedInvoice.customer}</dd></div>
              <div><dt>Subscription</dt><dd>{selectedInvoice.subscription}</dd></div>
              <div><dt>Date</dt><dd>{selectedInvoice.date}</dd></div>
              <div><dt>Due</dt><dd>{selectedInvoice.due}</dd></div>
              <div><dt>Total</dt><dd>{currency.format(selectedInvoice.total)}</dd></div>
              <div><dt>Status</dt><dd>{selectedInvoice.status}</dd></div>
            </dl>
            <div className="drawer-actions">
              <button className="primary-action" type="button">Mark as Confirmed</button>
              <button className="secondary-action" type="button">Send</button>
              <button className="secondary-action" type="button">Print</button>
            </div>
          </>
        )}
      </Drawer>
    </AppShell>
  );
}
