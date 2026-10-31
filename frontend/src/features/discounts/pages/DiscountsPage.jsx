import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

const discounts = [
  { code: 'SEATS10', type: 'Percentage', value: '10%', minimum: '10 seats', valid: '01 Oct - 31 Dec 2026', used: '4 / 20', appliesTo: 'CloudDesk Pro', status: 'Active' },
  { code: 'FLAT2000', type: 'Fixed', value: '₹2,000', minimum: '₹20,000', valid: '01 Nov - 30 Nov 2026', used: '0 / 50', appliesTo: 'All subscriptions', status: 'Draft' },
  { code: 'WELCOME5', type: 'Percentage', value: '5%', minimum: '—', valid: '01 Jan - 30 Sep 2026', used: '30 / 30', appliesTo: 'All subscriptions', status: 'Expired' },
];

export function DiscountsPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [selectedDiscount, setSelectedDiscount] = useState(null);
  const filteredDiscounts = useMemo(() => discounts.filter((discount) => (
    discount.code.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || discount.status === status)
  )), [query, status]);

  return (
    <AppShell title="Discounts" description="Rules applied automatically to the next invoice." breadcrumb="Brightloop / Discounts" activeNav="discounts" primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ Create discount</button>} secondaryAction={<button className="secondary-action" type="button">Export</button>}>
      <div className="discount-toolbar">
        <input className="discount-search" type="search" placeholder="Search discounts..." aria-label="Search discounts" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="discount-filter" aria-label="Filter discounts by status" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option>All statuses</option><option>Active</option><option>Draft</option><option>Expired</option>
        </select>
      </div>
      <div className="data-card discount-card">
        <table className="data-table discount-table">
          <thead><tr><th>Code</th><th>Type</th><th>Value</th><th>Minimum</th><th>Valid</th><th>Used</th><th>Applies to</th><th>Status</th></tr></thead>
          <tbody>{filteredDiscounts.map((discount) => <tr key={discount.code} className="clickable-row" tabIndex="0" onClick={() => setSelectedDiscount(discount)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setSelectedDiscount(discount); }}>
            <td><button className="table-link" type="button" onClick={() => setSelectedDiscount(discount)}>{discount.code}</button></td><td>{discount.type}</td><td>{discount.value}</td><td>{discount.minimum}</td><td>{discount.valid}</td><td>{discount.used}</td><td>{discount.appliesTo}</td>
            <td><span className={`status-pill ${discount.status === 'Active' ? 'success' : discount.status === 'Draft' ? 'warning' : 'muted'}`}><span className="dot" />{discount.status}</span></td>
          </tr>)}</tbody>
        </table>
        <div className="table-footer">Showing {filteredDiscounts.length} of {discounts.length} records</div>
      </div>
      <Drawer title={selectedDiscount?.code || 'Discount'} isOpen={Boolean(selectedDiscount)} onClose={() => setSelectedDiscount(null)} className="discount-detail-drawer">
        {selectedDiscount && (
          <>
            <span className={`status-pill ${selectedDiscount.status === 'Active' ? 'success' : selectedDiscount.status === 'Draft' ? 'warning' : 'muted'}`}><span className="dot" />{selectedDiscount.status}</span>
            <dl className="discount-detail-list">
              <div><dt>Code</dt><dd>{selectedDiscount.code}</dd></div>
              <div><dt>Type</dt><dd>{selectedDiscount.type}</dd></div>
              <div><dt>Value</dt><dd>{selectedDiscount.value}</dd></div>
              <div><dt>Minimum</dt><dd>{selectedDiscount.minimum}</dd></div>
              <div><dt>Valid</dt><dd>{selectedDiscount.valid}</dd></div>
              <div><dt>Used</dt><dd>{selectedDiscount.used}</dd></div>
              <div><dt>Applies to</dt><dd>{selectedDiscount.appliesTo}</dd></div>
              <div><dt>Status</dt><dd>{selectedDiscount.status}</dd></div>
            </dl>
          </>
        )}
      </Drawer>
      <Drawer title="Create discount" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer">
        <form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}>
          <label>Code<input required /></label>
          <label>Type<select defaultValue="Percentage"><option>Percentage</option><option>Fixed</option></select></label>
          <label>Value<input /></label>
          <label>Minimum purchase or qty<input /></label>
          <label>Valid<input /></label>
          <label>Usage limit<input /></label>
          <label>Applies to<input /></label>
          <button className="primary-action drawer-submit" type="submit">Save</button>
        </form>
      </Drawer>
    </AppShell>
  );
}
