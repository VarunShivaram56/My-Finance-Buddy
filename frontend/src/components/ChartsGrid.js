import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const PIE_COLORS = ["#e8a15b", "#f3c48d", "#c26c32", "#f7ddb9", "#8f9b57", "#d98a48"];

function Card({ title, children }) {
  return (
    <div className="currency-panel rounded-3xl bg-white/90 p-5 shadow-soft ring-1 ring-borderSoft">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-ink">{title}</h3>
      </div>
      <div className="h-80">{children}</div>
    </div>
  );
}

function ChartsGrid({ dashboard }) {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Card title="Category Breakdown">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={dashboard.categoryBreakdown} dataKey="value" nameKey="name" outerRadius={110} label>
              {dashboard.categoryBreakdown.map((entry, index) => (
                <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Monthly Spending">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dashboard.monthlySpending}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1dfcc" />
            <XAxis dataKey="month" stroke="#99613a" />
            <YAxis stroke="#99613a" />
            <Tooltip />
            <Bar dataKey="amount" fill="#e8a15b" radius={[10, 10, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Daily Spending Trend">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={dashboard.dailySpending}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1dfcc" />
            <XAxis dataKey="date" stroke="#99613a" />
            <YAxis stroke="#99613a" />
            <Tooltip />
            <Line type="monotone" dataKey="amount" stroke="#c26c32" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Top Merchants">
        <div className="space-y-3">
          {dashboard.topMerchants.length === 0 ? (
            <p className="text-slate-500">No merchant data yet.</p>
          ) : (
            dashboard.topMerchants.map((merchant, index) => (
              <div
                key={`${merchant.merchant}-${index}`}
                className="flex items-center justify-between rounded-2xl bg-skywash px-4 py-3"
              >
                <span className="font-medium text-ink">{merchant.merchant}</span>
                <span className="font-semibold text-slate-600">Rs {merchant.amount.toFixed(2)}</span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

export default ChartsGrid;
