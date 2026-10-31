import { useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';

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
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  return (
    <AppShell
      title="Products"
      description="What you sell, with cost, price and variants."
      breadcrumb="Brightloop / Products"
      activeNav="products"
      primaryAction={
        <button className="primary-action" type="button" onClick={() => setIsCreateOpen((prev) => !prev)}>
          + Create
        </button>
      }
      secondaryAction={<button className="secondary-action" type="button">Export</button>}
    >
      <div className={`customers-layout ${isCreateOpen ? 'with-form' : ''}`}>
        <div className="customers-list-panel">
          <div className="table-toolbar">
            <div className="search-box">Search products...</div>
            <div className="filter-select">All statuses ⌄</div>
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
                {products.map((product) => (
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

            <div className="table-footer">Showing 3 of 3 records</div>
          </div>
        </div>

        {isCreateOpen && (
          <aside className="customer-form-panel">
            <div className="customer-form-header">
              <h2>Create</h2>
              <button type="button" className="ghost-button" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </button>
            </div>

            <form className="customer-form">
              <label className="field-group compact-field">
                <span>Name</span>
                <input type="text" placeholder="" />
              </label>

              <label className="field-group compact-field">
                <span>Type</span>
                <select defaultValue="Software">
                  <option>Software</option>
                  <option>Add-on</option>
                  <option>Hardware</option>
                </select>
              </label>

              <label className="field-group compact-field">
                <span>Sales price</span>
                <input type="text" placeholder="" />
              </label>

              <label className="field-group compact-field">
                <span>Cost price</span>
                <input type="text" placeholder="" />
              </label>

              <label className="field-group compact-field">
                <span>Variants</span>
                <input type="text" placeholder="" />
              </label>

              <button type="submit" className="primary-button small-save">
                Save
              </button>
            </form>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
