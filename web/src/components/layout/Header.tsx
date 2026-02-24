import { useEffect, useState } from "react";
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
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 transition-all duration-300 ${
        scrolled
          ? "bg-surface-raised/95 backdrop-blur-xl border-b border-surface-border shadow-lg shadow-black/30"
          : "bg-surface-raised border-b border-surface-border/60"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-md bg-accent flex items-center justify-center shadow-lg shadow-red-900/30">
              <span className="text-white font-mono font-bold text-sm">MI</span>
            </div>
            <span className="font-display font-bold text-lg tracking-tight text-white">
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
                  className={`relative flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-semibold uppercase tracking-widest transition-all ${
                    active
                      ? "text-white bg-white/[0.06]"
                      : "text-gray-500 hover:text-gray-200 hover:bg-white/[0.03]"
                  }`}
                >
                  <Icon size={14} strokeWidth={active ? 2 : 1.5} />
                  <span className="hidden sm:inline">{label}</span>
                  {active && (
                    <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent rounded-full" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
