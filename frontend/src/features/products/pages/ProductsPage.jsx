import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

const products = [
  {
    name: 'CloudDesk Pro',
    type: 'Software',
    sales: '₹7,500',
    cost: '₹3,100',
    variants: 'Brand: Odoo (+₹560)',
    status: 'Active',
  },
  {
    name: 'Analytics Suite',
    type: 'Software',
    sales: '₹21,600',
    cost: '₹9,800',
    variants: 'Edition: Plus (+₹1,200)',
    status: 'Active',
  },
  {
    name: 'SecureVault',
    type: 'Add-on',
    sales: '₹1,400',
    cost: '₹520',
    variants: 'None',
    status: 'Active',
  },
];

export function ProductsPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const visibleProducts = useMemo(() => products.filter((product) => (
    `${product.name} ${product.type}`.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || product.status === status)
  )), [query, status]);

  return (
    <AppShell
      title="Products"
      description="What you sell, with cost, price and variants."
      breadcrumb="Brightloop / Products"
      activeNav="products"
      primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ Create</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <input className="table-search" type="search" placeholder="Search products..." aria-label="Search products" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="table-filter" aria-label="Filter products by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option></select>
      </div>

      <div className="data-card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Type</th>
              <th>Sales price</th>
              <th>Cost price</th>
              <th>Variants</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visibleProducts.map((product) => (
              <tr key={product.name}>
                <td className="product-name">{product.name}</td>
                <td>{product.type}</td>
                <td>{product.sales}</td>
                <td>{product.cost}</td>
                <td>{product.variants}</td>
                <td>
                  <span className={`status-pill ${product.status === 'Active' ? 'success' : 'muted'}`}>
                    <span className="dot" />
                    {product.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="table-footer">Showing {visibleProducts.length} of {products.length} records</div>
      </div>
      <Drawer title="Create" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}><label>Name<input required /></label><label>Type<select defaultValue="Software"><option>Software</option><option>Add-on</option><option>Service</option></select></label><label>Sales price<input inputMode="decimal" /></label><label>Cost price<input inputMode="decimal" /></label><label>Variants<input /></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
