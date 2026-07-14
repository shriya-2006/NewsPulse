import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#3f6690", "#e8722c", "#7c8894", "#2f8f5b"];

export default function PieChartCard({ title, data, labelKey = "label", dataKey = "count" }) {
  return (
    <div className="chart-card">
      <h3 className="chart-card__title">{title}</h3>
      {data.length === 0 ? (
        <p className="chart-card__empty">No data yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey={dataKey}
              nameKey={labelKey}
              cx="50%"
              cy="50%"
              outerRadius={72}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #d7dce1" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
