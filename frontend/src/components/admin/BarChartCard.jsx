import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const STEEL = "#3f6690";
const EMBER = "#e8722c";

export default function BarChartCard({
  title,
  data,
  dataKey = "count",
  labelKey = "label",
  color = STEEL,
  emptyText = "No data yet.",
  height = 240,
}) {
  return (
    <div className="chart-card">
      <h3 className="chart-card__title">{title}</h3>
      {data.length === 0 ? (
        <p className="chart-card__empty">{emptyText}</p>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis
              dataKey={labelKey}
              tick={{ fontSize: 11, fill: "#7c8894" }}
              angle={-20}
              textAnchor="end"
              height={50}
              interval={0}
            />
            <YAxis tick={{ fontSize: 11, fill: "#7c8894" }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #d7dce1" }}
            />
            <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export { STEEL, EMBER };
