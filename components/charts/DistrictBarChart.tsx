"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const MOCK_DATA = [
  { district: "Manhattan", trees: 87420, density: 1240 },
  { district: "Brooklyn", trees: 124300, density: 980 },
  { district: "Queens", trees: 156800, density: 820 },
  { district: "Bronx", trees: 98200, density: 1100 },
  { district: "Staten Is.", trees: 72100, density: 1380 },
  { district: "Midtown", trees: 34500, density: 680 },
  { district: "Harlem", trees: 52300, density: 920 },
];

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; name: string }[];
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded px-3 py-2 text-xs shadow-xl">
      <p className="font-semibold text-foreground mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="text-muted-foreground">
          {p.name}: <span className="text-primary font-medium">{p.value.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
};

export function DistrictBarChart() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={MOCK_DATA} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 20% 20%)" />
        <XAxis
          dataKey="district"
          tick={{ fill: "hsl(215 16% 55%)", fontSize: 11 }}
          axisLine={{ stroke: "hsl(215 20% 20%)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "hsl(215 16% 55%)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(34,197,94,0.05)" }} />
        <Bar dataKey="trees" name="Trees" radius={[2, 2, 0, 0]}>
          {MOCK_DATA.map((entry, i) => (
            <Cell
              key={entry.district}
              fill={i === 2 ? "#22c55e" : "hsl(215 20% 28%)"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DensityLineChart() {
  const timeData = [
    { month: "Jan", density: 820 },
    { month: "Feb", density: 835 },
    { month: "Mar", density: 850 },
    { month: "Apr", density: 910 },
    { month: "May", density: 980 },
    { month: "Jun", density: 1050 },
    { month: "Jul", density: 1090 },
    { month: "Aug", density: 1120 },
  ];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={timeData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 20% 20%)" />
        <XAxis
          dataKey="month"
          tick={{ fill: "hsl(215 16% 55%)", fontSize: 11 }}
          axisLine={{ stroke: "hsl(215 20% 20%)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "hsl(215 16% 55%)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="density"
          name="Trees/km²"
          stroke="#22c55e"
          strokeWidth={2}
          dot={{ fill: "#22c55e", r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
