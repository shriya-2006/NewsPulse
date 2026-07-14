import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { listReports, downloadReport } from "../api/reports.js";
import { ApiError } from "../api/client.js";
import Navbar from "../components/dashboard/Navbar.jsx";
import "./ReportsHistory.css";

const LANGUAGE_LABELS = { en: "English", te: "Telugu", hi: "Hindi" };

function formatDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function ReportsHistory() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    listReports(token)
      .then(setReports)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        setError(err instanceof ApiError ? err.message : "Could not load your reports.");
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleDownload = async (report) => {
    setDownloadingId(report.id);
    setDownloadError("");
    try {
      await downloadReport({
        downloadUrl: report.download_url,
        token,
        filename: `${report.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.pdf`,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setDownloadError(
        err instanceof ApiError ? err.message : "Could not download that report."
      );
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="dashboard">
      <Navbar />
      <main className="reports-history-content">
        <div className="reports-history-intro">
          <span className="reports-history-eyebrow">Your Reports</span>
          <h1>Report History</h1>
        </div>

        {isLoading && <p className="reports-history-status">Loading your reports…</p>}
        {error && <p className="reports-history-status reports-history-status--error">{error}</p>}
        {downloadError && (
          <p className="reports-history-status reports-history-status--error">{downloadError}</p>
        )}

        {!isLoading && !error && reports.length === 0 && (
          <div className="reports-history-empty">
            <h3>No reports yet</h3>
            <p>
              Search for news on the Dashboard, select the articles you want, and click
              "Generate Report" — it'll show up here once you do.
            </p>
          </div>
        )}

        {reports.length > 0 && (
          <div className="reports-history-table-card">
            <table className="reports-history-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Keyword</th>
                  <th>Language</th>
                  <th>Newspaper</th>
                  <th>Edition</th>
                  <th>Articles</th>
                  <th>Generated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>{r.title}</td>
                    <td>{r.keyword}</td>
                    <td>{LANGUAGE_LABELS[r.language] || r.language}</td>
                    <td>{r.newspaper || "All newspapers"}</td>
                    <td>{r.edition || "All editions"}</td>
                    <td>{r.article_count}</td>
                    <td>{formatDateTime(r.generated_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="reports-history-download-btn"
                        onClick={() => handleDownload(r)}
                        disabled={downloadingId === r.id}
                      >
                        {downloadingId === r.id ? "Downloading…" : "Download"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
