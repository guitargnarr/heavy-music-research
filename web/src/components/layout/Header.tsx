import { Link, useLocation } from "react-router-dom";
import { BarChart3, Network, Calendar, Info } from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: BarChart3 },
  { to: "/network", label: "Network", icon: Network },
  { to: "/tours", label: "Tours", icon: Calendar },
  { to: "/about", label: "About", icon: Info },
];

export function Header() {
  const { pathname } = useLocation();

  return (
    <header className="border-b border-surface-border bg-surface-raised/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-brand-red flex items-center justify-center">
              <span className="text-white font-bold text-sm">MI</span>
            </div>
            <span className="font-bold text-lg text-gray-100 group-hover:text-white transition-colors">
              Metalcore Index
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => {
              const active =
                to === "/" ? pathname === "/" : pathname.startsWith(to);
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-brand-red/10 text-brand-red-light"
                      : "text-gray-400 hover:text-gray-200 hover:bg-surface-overlay"
                  }`}
                >
                  <Icon size={16} />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
