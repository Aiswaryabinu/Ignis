import { useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

const payments = [
  { reference: 'PAY-501', invoice: 'INV-1044', method: 'UPI', amount: '₹8,850', date: '03 Oct 2026', note: 'Matched to bank ref' },
  { reference: 'PAY-500', invoice: 'INV-1041', method: 'Bank transfer', amount: '₹1,09,150', date: '12 Sep 2026', note: 'Full payment' },
  { reference: 'PAY-499', invoice: 'INV-1043', method: 'Card', amount: '₹1,00,000', date: '20 Oct 2026', note: 'Part payment' },
];

export function PaymentsPage() {
  const [query, setQuery] = useState('');
  const [isRecordOpen, setRecordOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const filteredPayments = payments.filter((payment) => [payment.reference, payment.invoice, payment.note].some((value) => value.toLowerCase().includes(query.toLowerCase())));

  return (
    <AppShell title="Payments" description="Every payment against its invoice." breadcrumb="Brightloop / Payments" activeNav="payments" primaryAction={<button className="primary-action" type="button" onClick={() => setRecordOpen(true)}>+ Record payment</button>} secondaryAction={<button className="secondary-action" type="button">Export</button>}>
      <div className="payment-toolbar"><input className="payment-search" type="search" placeholder="Search payments..." aria-label="Search payments" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      <div className="data-card payment-card">
        <table className="data-table payment-table">
          <thead><tr><th>Reference</th><th>Invoice</th><th>Method</th><th className="amount-column">Amount</th><th>Date</th><th>Note</th></tr></thead>
          <tbody>{filteredPayments.map((payment) => <tr key={payment.reference}><td><button className="table-link" type="button" onClick={() => setSelectedPayment(payment)}>{payment.reference}</button></td><td>{payment.invoice}</td><td>{payment.method}</td><td className="amount-column">{payment.amount}</td><td>{payment.date}</td><td>{payment.note}</td></tr>)}</tbody>
        </table>
        <div className="table-footer">Showing {filteredPayments.length} of {payments.length} records</div>
      </div>
      <Drawer title={selectedPayment?.reference || 'Payment'} isOpen={Boolean(selectedPayment)} onClose={() => setSelectedPayment(null)} className="payment-detail-drawer">
        {selectedPayment && <dl className="detail-list"><div><dt>Reference</dt><dd>{selectedPayment.reference}</dd></div><div><dt>Invoice</dt><dd>{selectedPayment.invoice}</dd></div><div><dt>Method</dt><dd>{selectedPayment.method}</dd></div><div><dt>Amount</dt><dd>{selectedPayment.amount}</dd></div><div><dt>Date</dt><dd>{selectedPayment.date}</dd></div><div><dt>Note</dt><dd>{selectedPayment.note}</dd></div></dl>}
      </Drawer>
      <Drawer title="Record payment" isOpen={isRecordOpen} onClose={() => setRecordOpen(false)} className="form-drawer">
        <form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setRecordOpen(false); }}>
          <label>Invoice<select defaultValue="INV-1052"><option>INV-1052</option><option>INV-1043</option><option>INV-1044</option></select></label>
          <label>Method<select defaultValue="UPI"><option>UPI</option><option>Bank transfer</option><option>Card</option></select></label>
          <label>Amount<input inputMode="decimal" /></label>
          <label>Date<input type="date" /></label>
          <label>Note<input /></label>
          <button className="primary-action drawer-submit" type="submit">Save</button>
        </form>
      </Drawer>
    </AppShell>
  );
}
