import { useRef, useState } from "react";
import "./App.css";

const BACKEND_URL = "http://127.0.0.1:8000";

function App() {
  // Receipt OCR state
  const [receiptFile, setReceiptFile] = useState(null);
  const [receiptResult, setReceiptResult] = useState(null);
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [receiptError, setReceiptError] = useState("");

  // CSV / anomaly state
  const [csvFile, setCsvFile] = useState(null);
  const [anomalyResult, setAnomalyResult] = useState(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [anomalyError, setAnomalyError] = useState("");
  const [contamination, setContamination] = useState(0.05);
  const [topN, setTopN] = useState(20);

  // Refs to reset file inputs
  const receiptInputRef = useRef(null);
  const csvInputRef = useRef(null);

  // Clear handlers
  const handleClearReceipt = () => {
    setReceiptFile(null);
    setReceiptResult(null);
    setReceiptError("");
    if (receiptInputRef.current) {
      receiptInputRef.current.value = "";
    }
  };

  const handleClearCsv = () => {
    setCsvFile(null);
    setAnomalyResult(null);
    setAnomalyError("");
    if (csvInputRef.current) {
      csvInputRef.current.value = "";
    }
  };

  const handleReceiptSubmit = async (e) => {
    e.preventDefault();
    setReceiptError("");
    setReceiptResult(null);

    if (!receiptFile) {
      setReceiptError("Please select an image file first.");
      return;
    }

    try {
      setReceiptLoading(true);

      const formData = new FormData();
      formData.append("file", receiptFile);

      const response = await fetch(`${BACKEND_URL}/api/parse-receipt`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to parse receipt.");
      }

      const data = await response.json();
      setReceiptResult(data);
    } catch (err) {
      setReceiptError(err.message || "Something went wrong.");
    } finally {
      setReceiptLoading(false);
    }
  };

  const handleCsvSubmit = async (e) => {
    e.preventDefault();
    setAnomalyError("");
    setAnomalyResult(null);

    if (!csvFile) {
      setAnomalyError("Please select a CSV file first.");
      return;
    }

    try {
      setAnomalyLoading(true);

      const formData = new FormData();
      formData.append("file", csvFile);
      formData.append("contamination", contamination);
      formData.append("top_n", topN);

      const response = await fetch(
        `${BACKEND_URL}/api/analyze-transactions`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to analyze transactions.");
      }

      const data = await response.json();
      setAnomalyResult(data);
    } catch (err) {
      setAnomalyError(err.message || "Something went wrong.");
    } finally {
      setAnomalyLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="bg-gradient" />

      <header className="topbar">
        <div className="topbar-left">
          <div className="logo-pill">
            <span className="logo-dot">FG</span>
          </div>
          <div>
            <h1 className="app-title">FinGuard AI</h1>
            <p className="app-subtitle">
              AI-driven expense auditing & fraud signaling dashboard
            </p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="pill pill-live">
            <span className="pill-dot" /> Backend: localhost:8000
          </span>
        </div>
      </header>

      <main className="app-main">
        <section className="intro-strip">
          <p>
            Upload receipts and transaction exports to get automatic OCR, clean
            parsing, and anomaly scores. Designed for small teams that want
            quick financial sanity checks without heavy tooling.
          </p>
        </section>

        {/* Sample data helper */}
        <section className="sample-strip">
          <div className="sample-text">
            <strong>Need something to test with?</strong>{" "}
            Use sample files to see FinGuard AI in action.
          </div>
          <div className="sample-actions">
            {/* Update these hrefs once you add real sample files in your repo */}
            <a
              className="btn-secondary"
              href="https://github.com/MitchelMutulii/FinGuard-AI/tree/main/data/sample_receipts"
              target="_blank"
              rel="noreferrer"
            >
              View sample receipt
            </a>
            <a
              className="btn-secondary"
              href="https://github.com/MitchelMutulii/FinGuard-AI/tree/main/data"
              target="_blank"
              rel="noreferrer"
            >
              Sample transactions CSV
            </a>
          </div>
        </section>

        <section className="cards-grid">
          {/* Receipt OCR section */}
          <section className="card">
            <div className="card-header">
              <div>
                <h2>1. Receipt OCR & Parsing</h2>
                <p>
                  Convert raw receipt images into structured data: merchant,
                  date, and total. Powered by Tesseract OCR and preprocessing.
                </p>
              </div>
              <span className="badge badge-blue">Image → JSON</span>
            </div>

            <form onSubmit={handleReceiptSubmit} className="form">
              <label className="field-label">Receipt image</label>
              <input
                type="file"
                accept="image/*"
                ref={receiptInputRef}
                onChange={(e) => setReceiptFile(e.target.files[0] || null)}
              />

              <div className="button-row">
                <button type="submit" disabled={receiptLoading}>
                  {receiptLoading ? "Processing..." : "Upload & Parse"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleClearReceipt}
                >
                  Clear
                </button>
              </div>
            </form>

            {receiptError && (
              <div className="alert alert-error">
                <strong>Error:</strong> {receiptError}
              </div>
            )}

            {receiptResult && (
              <div className="panel">
                <div className="panel-header">
                  <h3>Parsed receipt</h3>
                  <span className="tag">
                    {receiptResult.filename || "uploaded image"}
                  </span>
                </div>

                <dl className="kv-list">
                  <div>
                    <dt>Merchant</dt>
                    <dd>{receiptResult.parsed_receipt.merchant || "N/A"}</dd>
                  </div>
                  <div>
                    <dt>Date</dt>
                    <dd>{receiptResult.parsed_receipt.date || "N/A"}</dd>
                  </div>
                  <div>
                    <dt>Total amount</dt>
                    <dd>
                      {receiptResult.parsed_receipt.total_amount ?? "N/A"}
                    </dd>
                  </div>
                </dl>

                <details className="details-raw">
                  <summary>View raw OCR text</summary>
                  <pre>{receiptResult.parsed_receipt.raw_text}</pre>
                </details>
              </div>
            )}
          </section>

          {/* Anomaly detection section */}
          <section className="card">
            <div className="card-header">
              <div>
                <h2>2. Transaction Anomaly Detection</h2>
                <p>
                  Upload a CSV export from your banking or accounting tool.
                  FinGuard AI learns what “normal” looks like and ranks the most
                  suspicious rows.
                </p>
              </div>
              <span className="badge badge-purple">CSV → Risk scores</span>
            </div>

            <form onSubmit={handleCsvSubmit} className="form">
              <label className="field-label">Transactions CSV file</label>
              <input
                type="file"
                accept=".csv,text/csv"
                ref={csvInputRef}
                onChange={(e) => setCsvFile(e.target.files[0] || null)}
              />

              <div className="form-row">
                <label>
                  Contamination (expected anomaly fraction)
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="0.3"
                    value={contamination}
                    onChange={(e) =>
                      setContamination(parseFloat(e.target.value) || 0.05)
                    }
                  />
                </label>

                <label>
                  Top N suspicious
                  <input
                    type="number"
                    min="1"
                    max="200"
                    value={topN}
                    onChange={(e) =>
                      setTopN(parseInt(e.target.value || "20", 10))
                    }
                  />
                </label>
              </div>

              <div className="button-row">
                <button type="submit" disabled={anomalyLoading}>
                  {anomalyLoading ? "Analyzing..." : "Upload & Analyze"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleClearCsv}
                >
                  Clear
                </button>
              </div>
            </form>

            {anomalyError && (
              <div className="alert alert-error">
                <strong>Error:</strong> {anomalyError}
              </div>
            )}

            {anomalyResult && (
              <div className="panel">
                <div className="panel-header">
                  <h3>Suspicious transactions</h3>
                  <span className="tag">
                    {anomalyResult.returned_transactions} /{" "}
                    {anomalyResult.total_transactions} shown
                  </span>
                </div>

                <p className="panel-subtitle">
                  Sorted by anomaly score (1.0 = most suspicious).
                </p>

                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(
                          anomalyResult.anomalies[0] || {}
                        ).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {anomalyResult.anomalies.map((row, idx) => (
                        <tr key={idx}>
                          {Object.entries(row).map(([key, value]) => (
                            <td key={key}>{String(value)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </section>
      </main>

      <footer className="app-footer">
        <p>FinGuard AI · AI-Driven Smart Finance Hackathon</p>
      </footer>
    </div>
  );
}

export default App;
