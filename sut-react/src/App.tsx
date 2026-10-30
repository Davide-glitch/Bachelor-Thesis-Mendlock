import React, { useState } from "react";
import { ProductItem, ReleaseVersion } from "./types";

const PRODUCTS_V1: ProductItem[] = [
  { sku: "gpu-4070", name: "RTX 4070 Ti Workstation", price: "$1,499", spec: "16GB RAM, NVMe 1TB" },
  { sku: "kb-mech", name: "Tactile Mechanical Keyboard", price: "$149", spec: "Hot-swappable switches" },
  { sku: "mon-4k", name: "27-inch 4K IPS Monitor", price: "$399", spec: "144Hz, USB-C PD" },
  { sku: "dock-tb4", name: "Thunderbolt 4 Pro Dock", price: "$229", spec: "Dual 4K, 96W charging" },
];

// In v2, the product grid order is shuffled
const PRODUCTS_V2: ProductItem[] = [
  PRODUCTS_V1[2],
  PRODUCTS_V1[3],
  PRODUCTS_V1[0],
  PRODUCTS_V1[1],
];

const NAV_LINKS = ["Dashboard", "Catalog", "Transfers", "Invoices", "Analytics", "Compliance", "Support"];
const SIDEBAR_FILTERS = ["All Departments", "Hardware", "Cloud Credits", "Security Keys", "Archived"];

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const release: ReleaseVersion = params.get("release") === "v2" ? "v2" : "v1";

  const [statusBanner, setStatusBanner] = useState<string>("");
  const [toastAlert, setToastAlert] = useState<string>("");

  const triggerSideEffect = (actionKey: string, bannerText: string, isToast: boolean, httpMethod?: string) => {
    window.localStorage.setItem("mendlock_last_action", actionKey);
    if (httpMethod) {
      fetch(`http://127.0.0.1:9/api/${actionKey}`, {
        method: httpMethod,
        body: JSON.stringify({ actionKey, release }),
        mode: "no-cors",
      }).catch(() => {});
    }
    if (isToast) {
      setToastAlert(bannerText);
    } else {
      setStatusBanner(bannerText);
    }
  };

  const btnPrimary: React.CSSProperties = {
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    padding: "8px 16px",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: 600,
  };

  const btnSecondary: React.CSSProperties = {
    background: "#e5e7eb",
    color: "#111827",
    border: "1px solid #d1d5db",
    padding: "8px 16px",
    borderRadius: "6px",
    cursor: "pointer",
  };

  const btnDanger: React.CSSProperties = {
    background: "#dc2626",
    color: "#ffffff",
    border: "none",
    padding: "8px 16px",
    borderRadius: "6px",
    cursor: "pointer",
  };

  const products = release === "v1" ? PRODUCTS_V1 : PRODUCTS_V2;

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "20px" }}>
      {/* Top Navigation Chrome (7 interactive links) */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#1e293b",
          color: "#fff",
          padding: "12px 20px",
          borderRadius: "8px",
          marginBottom: "20px",
        }}
      >
        <div style={{ fontWeight: 700, fontSize: "18px" }}>
          Mendlock Enterprise SUT ({release.toUpperCase()})
        </div>
        <nav style={{ display: "flex", gap: "14px" }}>
          {NAV_LINKS.map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              onClick={(e) => {
                e.preventDefault();
                triggerSideEffect(`nav_${item}`, `Navigated to ${item}`, true);
              }}
              style={{ color: "#cbd5e1", textDecoration: "none", fontSize: "14px" }}
            >
              {item}
            </a>
          ))}
        </nav>
      </header>

      {/* Status & Toast Oracles */}
      {statusBanner && (
        <div
          id="status-banner"
          role="status"
          style={{
            background: "#dcfce7",
            color: "#166534",
            padding: "12px 16px",
            borderRadius: "6px",
            marginBottom: "16px",
            fontWeight: 600,
          }}
        >
          {statusBanner}
        </div>
      )}
      {toastAlert && (
        <div
          id="toast-alert"
          role="alert"
          style={{
            background: "#fef3c7",
            color: "#92400e",
            padding: "12px 16px",
            borderRadius: "6px",
            marginBottom: "16px",
          }}
        >
          {toastAlert}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "20px" }}>
        {/* Left Sidebar Chrome (5 interactive filter buttons) */}
        <aside
          style={{
            background: "#fff",
            padding: "16px",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <h3 style={{ margin: "0 0 8px", fontSize: "15px" }}>Department Filters</h3>
          {SIDEBAR_FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              style={btnSecondary}
              onClick={() => triggerSideEffect(`filter_${f}`, `Filter applied: ${f}`, true)}
            >
              {f}
            </button>
          ))}
        </aside>

        {/* Main Workspace */}
        <main style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* SCENARIO 1: Hardware Catalog Grid (Context + Reorder + Hash Churn) */}
          <section style={{ background: "#fff", padding: "20px", borderRadius: "8px" }}>
            <h2 style={{ margin: "0 0 12px", fontSize: "18px" }}>1. Hardware Procurement Catalog</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "12px" }}>
              {products.map((prod, idx) => (
                <div
                  key={prod.sku}
                  className={release === "v1" ? "product-card" : `sc-card-${idx}`}
                  style={{ border: "1px solid #e5e7eb", padding: "14px", borderRadius: "6px" }}
                >
                  <h3 style={{ margin: "0 0 4px", fontSize: "16px" }}>{prod.name}</h3>
                  <p style={{ margin: "0 0 10px", color: "#6b7280", fontSize: "13px" }}>
                    {prod.price} — {prod.spec}
                  </p>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      type="button"
                      id={release === "v1" ? `add-${prod.sku}` : `:r1${idx}:`}
                      className={release === "v1" ? `btn-add-${prod.sku}` : `css-99a1${idx}`}
                      data-gt={prod.sku === "gpu-4070" ? "1" : undefined}
                      style={btnPrimary}
                      onClick={() =>
                        triggerSideEffect(
                          `cart_${prod.sku}`,
                          prod.sku === "gpu-4070"
                            ? "Added RTX 4070 Ti Workstation to cart"
                            : `Added ${prod.name} to cart`,
                          prod.sku !== "gpu-4070"
                        )
                      }
                    >
                      {release === "v1" ? "Add to Cart" : "Add to Basket"}
                    </button>
                    <button
                      type="button"
                      style={btnSecondary}
                      onClick={() => triggerSideEffect(`wish_${prod.sku}`, `Saved ${prod.name}`, true)}
                    >
                      Save Spec
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* SCENARIO 2: Order Checkout (ID/Class Churn + Decoy Preview Button) */}
          <section style={{ background: "#fff", padding: "20px", borderRadius: "8px" }}>
            <h2 style={{ margin: "0 0 8px", fontSize: "18px" }}>2. Express Checkout</h2>
            <p style={{ margin: "0 0 12px", color: "#4b5563", fontSize: "14px" }}>
               Total due: $1,499.00 — Corporate Invoice #INV-2026
            </p>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              {/* Look-alike decoy that fires a POST request and shows a toast */}
              <button
                type="button"
                id={release === "v1" ? "btn-preview-order" : "ember-8821"}
                style={btnSecondary}
                onClick={() =>
                  triggerSideEffect("preview_order", "Order preview generated", true, "POST")
                }
              >
                Place Order Preview
              </button>

              {/* Target button */}
              <button
                type="button"
                id={release === "v1" ? "place-order-btn" : "radix-77412"}
                className={release === "v1" ? "btn-checkout-submit" : "tw-bg-blue-600"}
                style={btnPrimary}
                onClick={() =>
                  triggerSideEffect("commit_order", "Corporate order #INV-2026 confirmed", false)
                }
              >
                Place Order
              </button>

              <button
                type="button"
                style={btnDanger}
                onClick={() =>
                  triggerSideEffect("cancel_order", "Checkout cancelled", true, "DELETE")
                }
              >
                Cancel Order
              </button>
            </div>
          </section>

          {/* SCENARIO 3: Wire Transfer (Restyle + DOM Wrapping) */}
          <section style={{ background: "#fff", padding: "20px", borderRadius: "8px" }}>
            <h2 style={{ margin: "0 0 8px", fontSize: "18px" }}>3. Treasury Wire Transfer</h2>
            <p style={{ margin: "0 0 12px", color: "#4b5563", fontSize: "14px" }}>
              Beneficiary: Supplier IBAN RO49AAAA1B31007593840000
            </p>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {release === "v1" ? (
                <button
                  type="button"
                  id="send-wire-btn"
                  className="js-send-wire"
                  style={btnPrimary}
                  onClick={() => triggerSideEffect("wire_sent", "Wire transfer dispatched", false)}
                >
                  Send Transfer
                </button>
              ) : (
                <div className="w-outer">
                  <div className="w-inner">
                    <button
                      type="button"
                      className="css-restyled-wire"
                      style={btnSecondary}
                      onClick={() => triggerSideEffect("wire_sent", "Wire transfer dispatched", false)}
                    >
                      Send Transfer
                    </button>
                  </div>
                </div>
              )}

              <button
                type="button"
                style={release === "v1" ? btnSecondary : btnPrimary}
                onClick={() => triggerSideEffect("wire_sched", "Transfer scheduled for tomorrow", true)}
              >
                Schedule Transfer
              </button>
            </div>
          </section>

          {/* SCENARIO 4: Security Preferences (Label Shift + Tag Change + Destructive Decoy) */}
          <section style={{ background: "#fff", padding: "20px", borderRadius: "8px" }}>
            <h2 style={{ margin: "0 0 8px", fontSize: "18px" }}>4. Security & API Policies</h2>
            <p style={{ margin: "0 0 12px", color: "#4b5563", fontSize: "14px" }}>
              Rotate SSH keys and enforce hardware 2FA tokens.
            </p>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {release === "v1" ? (
                <button
                  type="button"
                  id="save-security-btn"
                  style={btnPrimary}
                  onClick={() => triggerSideEffect("sec_saved", "Security policy updated", false)}
                >
                  Save Changes
                </button>
              ) : (
                <a
                  href="#save"
                  role="button"
                  className="sc-link-btn"
                  style={{ ...btnPrimary, textDecoration: "none", display: "inline-block" }}
                  onClick={(e) => {
                    e.preventDefault();
                    triggerSideEffect("sec_saved", "Security policy updated", false);
                  }}
                >
                  Update Profile Policy
                </a>
              )}

              <button
                type="button"
                style={btnSecondary}
                onClick={() => triggerSideEffect("sec_reset", "Defaults restored", true)}
              >
                Reset to Defaults
              </button>

              <button
                type="button"
                style={btnDanger}
                onClick={() =>
                  triggerSideEffect("sec_revoke", "All API tokens revoked", true, "DELETE")
                }
              >
                Revoke All Keys
              </button>

              {/* SCENARIO 5: Removed Feature in v2 */}
              {release === "v1" && (
                <button
                  type="button"
                  id="export-legacy-xml"
                  style={btnSecondary}
                  onClick={() => triggerSideEffect("xml_export", "Legacy XML exported", false)}
                >
                  Export Legacy XML
                </button>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}