export function StatCard({ label, value, accent }) {
  return (
    <div>
      <p>{label}</p>
      <h3 style={{ color: accent }}>{value}</h3>
    </div>
  );
}
