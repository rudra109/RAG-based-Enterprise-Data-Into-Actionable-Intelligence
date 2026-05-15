import { 
  Activity, 
  Users, 
  Database, 
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight
} from "lucide-react";

export default function Home() {
  const stats = [
    { name: "Active Queries", value: "1,284", change: "+12.5%", trend: "up", icon: Activity },
    { name: "Data Points", value: "4.2M", change: "+3.2%", trend: "up", icon: Database },
    { name: "Anomalies", value: "12", change: "-25%", trend: "down", icon: ShieldCheck },
    { name: "Active Users", value: "854", change: "+1.2%", trend: "up", icon: Users },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard Overview</h1>
        <p className="text-slate-400">Welcome back! Here's what's happening with EnterpriseIQ today.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.name} className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 transition-hover hover:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-brand-600/10 p-2">
                <stat.icon className="h-6 w-6 text-brand-400" />
              </div>
              <div className={cn(
                "flex items-center gap-0.5 text-sm font-medium",
                stat.trend === "up" ? "text-emerald-500" : "text-rose-500"
              )}>
                {stat.trend === "up" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                {stat.change}
              </div>
            </div>
            <div className="mt-4">
              <h2 className="text-sm font-medium text-slate-400">{stat.name}</h2>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h3 className="text-lg font-medium text-white mb-4">System Performance</h3>
          <div className="h-[240px] flex items-center justify-center border border-dashed border-slate-700 rounded-lg bg-slate-800/20">
            <p className="text-slate-500 text-sm italic">Analytics Visualization Placeholder</p>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Recent Anomalies</h3>
          <div className="h-[240px] flex items-center justify-center border border-dashed border-slate-700 rounded-lg bg-slate-800/20">
            <p className="text-slate-500 text-sm italic">Anomalies List Placeholder</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(" ");
}
