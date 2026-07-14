import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { fetchAdminDashboard, fetchAdminUsers } from "../api/admin.js";
import { ApiError } from "../api/client.js";
import Navbar from "../components/dashboard/Navbar.jsx";
import StatCard from "../components/admin/StatCard.jsx";
import BarChartCard, { EMBER, STEEL } from "../components/admin/BarChartCard.jsx";
import PieChartCard from "../components/admin/PieChartCard.jsx";
import "./AdminDashboard.css";

function formatDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function AdminDashboard() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAdminDashboard(token), fetchAdminUsers(token)])
      .then(([dashboardData, usersData]) => {
        setDashboard(dashboardData);
        setUsers(usersData.users);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load the admin dashboard."
        );
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="dashboard">
      <Navbar />
      <main className="admin-content">
        <div className="admin-intro">
          <span className="admin-eyebrow">Admin</span>
          <h1>Organization Overview</h1>
        </div>

        {isLoading && <p className="admin-status-text">Loading dashboard…</p>}
        {error && <p className="admin-status-text admin-status-text--error">{error}</p>}

        {dashboard && (
          <>
            <section className="admin-stats-grid">
              <StatCard label="Total Users" value={dashboard.overview.total_users} />
              <StatCard
                label="Active Users"
                value={dashboard.overview.active_users}
                sublabel="logged in, last 30 days"
              />
              <StatCard label="Reports Generated" value={dashboard.overview.total_reports} />
              <StatCard label="Search Count" value={dashboard.overview.total_searches} />
            </section>

            <section className="admin-charts-grid">
              <BarChartCard
                title="Most Searched Keywords"
                data={dashboard.most_searched_keywords}
                color={STEEL}
              />
              <PieChartCard title="Most Selected Language" data={dashboard.most_selected_language} />
              <BarChartCard
                title="Most Selected Newspaper"
                data={dashboard.most_selected_newspaper}
                color={EMBER}
                emptyText="No newspaper-specific searches yet."
              />
              <BarChartCard
                title="Most Selected Edition"
                data={dashboard.most_selected_edition}
                color={STEEL}
                emptyText="No edition-specific searches yet."
              />
              <BarChartCard
                title="Daily Reports (last 14 days)"
                data={dashboard.daily_reports.map((d) => ({ label: d.period.slice(5), count: d.count }))}
                color={EMBER}
                height={220}
              />
              <BarChartCard
                title="Monthly Reports (last 12 months)"
                data={dashboard.monthly_reports.map((d) => ({ label: d.period, count: d.count }))}
                color={STEEL}
                height={220}
              />
            </section>

            <section className="admin-tables-grid">
              <div className="admin-table-card">
                <h3>Recent Searches</h3>
                {dashboard.recent_searches.length === 0 ? (
                  <p className="chart-card__empty">No searches yet.</p>
                ) : (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Keyword</th>
                        <th>Newspaper</th>
                        <th>Results</th>
                        <th>When</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_searches.map((s) => (
                        <tr key={s.id}>
                          <td>{s.user_full_name}</td>
                          <td>{s.keyword}</td>
                          <td>{s.newspaper || "—"}</td>
                          <td>{s.result_count}</td>
                          <td>{formatDateTime(s.searched_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="admin-table-card">
                <h3>Recent Reports</h3>
                {dashboard.recent_reports.length === 0 ? (
                  <p className="chart-card__empty">No reports yet.</p>
                ) : (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Title</th>
                        <th>Articles</th>
                        <th>When</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_reports.map((r) => (
                        <tr key={r.id}>
                          <td>{r.user_full_name}</td>
                          <td>{r.title}</td>
                          <td>{r.article_count}</td>
                          <td>{formatDateTime(r.generated_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>

            <section className="admin-table-card admin-table-card--full">
              <h3>User Activity</h3>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Searches</th>
                    <th>Reports</th>
                    <th>Last login</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.full_name}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`role-badge ${u.is_admin ? "role-badge--admin" : ""}`}>
                          {u.is_admin ? "Admin" : "User"}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${u.is_active ? "status-badge--active" : "status-badge--inactive"}`}>
                          {u.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>
                      <td>{u.search_count}</td>
                      <td>{u.report_count}</td>
                      <td>{formatDateTime(u.last_login_at)}</td>
                      <td>{formatDateTime(u.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
