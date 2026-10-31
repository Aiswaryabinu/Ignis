import { useState, useEffect } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { downloadCsv } from '../../../lib/exportCsv.js';

const products = [
  {
    id: 1,
    name: 'CloudDesk Pro',
    type: 'Software',
    sales: '₹7,500',
    cost: '₹3,100',
    variants: 'Brand: Odoo (+₹560)',
    status: 'Active',
  },
  {
    id: 2,
    name: 'Analytics Suite',
    type: 'Software',
    sales: '₹21,600',
    cost: '₹9,800',
    variants: 'Edition: Plus (+₹1,200)',
    status: 'Active',
  },
  {
    id: 3,
    name: 'SecureVault',
    type: 'Add-on',
    sales: '₹1,400',
    cost: '₹520',
    variants: 'None',
    status: 'Active',
  },
];

function getInitials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export function ProductsPage() {
  const [productRows, setProductRows] = useState(products);
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const exportProducts = () => downloadCsv('products.csv', productRows);

  const isOpen = drawerMode !== null;

  useEffect(() => {
    const mainPanel = document.querySelector('.main-panel');
    if (!mainPanel) return;

    if (isOpen) {
      mainPanel.classList.add('drawer-push');
    } else {
      mainPanel.classList.remove('drawer-push');
    }

    return () => mainPanel.classList.remove('drawer-push');
  }, [isOpen]);

  function openCreate() {
    setSelectedProduct(null);
    setDrawerMode('create');
  }

  function openDetail(product) {
    setSelectedProduct(product);
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedProduct(null);
  }

  return (
    <AppShell
      title="Products"
      description="What you sell, with cost, price and variants."
      breadcrumb="Brightloop / Products"
      activeNav="products"
      primaryAction={
        <button className="primary-action" type="button" onClick={openCreate}>
          + Create
        </button>
      }
      secondaryAction={<button className="secondary-action" type="button" onClick={exportProducts}>Export</button>}
    >
      <aside className={`customer-drawer ${isOpen ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && (
          <>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-eyebrow">New Record</span>
                <h2 className="drawer-title">{selectedProduct ? 'Edit Product' : 'Create Product'}</h2>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />
            <p className="drawer-subtitle">Add a new product and its pricing details.</p>

            <form
              className="drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                const values = new FormData(e.currentTarget);
                const next = {
                  id: selectedProduct?.id || Date.now(),
                  name: values.get('name'),
                  type: values.get('type'),
                  sales: values.get('sales'),
                  cost: values.get('cost'),
                  variants: values.get('variants') || 'None',
                  status: selectedProduct?.status || 'Active',
                };
                setProductRows((current) => selectedProduct ? current.map((item) => item.id === selectedProduct.id ? next : item) : [...current, next]);
                closeDrawer();
              }}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Name</span>
                <input name="name" type="text" className="drawer-input" defaultValue={selectedProduct?.name || ''} placeholder="e.g. CloudDesk Pro" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Type</span>
                <select name="type" className="drawer-input" defaultValue={selectedProduct?.type || 'Software'}>
                  <option>Software</option>
                  <option>Add-on</option>
                  <option>Hardware</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Sales price</span>
                <input name="sales" type="text" className="drawer-input" defaultValue={selectedProduct?.sales || ''} placeholder="₹7,500" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Cost price</span>
                <input name="cost" type="text" className="drawer-input" defaultValue={selectedProduct?.cost || ''} placeholder="₹3,100" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Variants</span>
                <input name="variants" type="text" className="drawer-input" defaultValue={selectedProduct?.variants || ''} placeholder="Brand: Odoo (+₹560)" />
              </label>

              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save Product</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedProduct && (
          <>
            <div className="drawer-detail-header">
              <div className="drawer-detail-avatar">{getInitials(selectedProduct.name)}</div>
              <div className="drawer-detail-title-group">
                <span className="drawer-eyebrow">Product</span>
                <h2 className="drawer-title">{selectedProduct.name}</h2>
                <span className={`status-pill ${selectedProduct.status === 'Active' ? 'success' : 'muted'}`} style={{ marginTop: '6px', display: 'inline-flex' }}>
                  <span className="dot" />
                  {selectedProduct.status}
                </span>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-stats-row">
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedProduct.sales}</span>
                <span className="drawer-stat-label">Sales</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedProduct.cost}</span>
                <span className="drawer-stat-label">Cost</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedProduct.type}</span>
                <span className="drawer-stat-label">Type</span>
              </div>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-detail-body">
              <div className="drawer-detail-section-label">Product details</div>

              <div className="drawer-detail-grid">
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Name</span>
                  <span className="drawer-detail-val">{selectedProduct.name}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Type</span>
                  <span className="drawer-detail-val">{selectedProduct.type}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Sales price</span>
                  <span className="drawer-detail-val">{selectedProduct.sales}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Cost price</span>
                  <span className="drawer-detail-val">{selectedProduct.cost}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Variants</span>
                  <span className="drawer-detail-val">{selectedProduct.variants}</span>
                </div>
              </div>
            </div>

            <div className="drawer-actions" style={{ marginTop: 'auto' }}>
              <button type="button" className="drawer-save-btn" onClick={() => setDrawerMode('create')}>Edit Product</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
        )}
      </aside>

      <div className="customers-layout">
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
                {productRows.map((product) => (
                  <tr
                    key={product.id}
                    className={`customer-row ${selectedProduct?.id === product.id && drawerMode === 'detail' ? 'customer-row--active' : ''}`}
                    onClick={() => openDetail(product)}
                  >
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
      </div>
    </AppShell>
  );
}
