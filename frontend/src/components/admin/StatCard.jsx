export default function StatCard({ label, value, sublabel }) {
  return (
    <div className="stat-card">
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {sublabel && <span className="stat-card__sublabel">{sublabel}</span>}
    </div>
  );
}
