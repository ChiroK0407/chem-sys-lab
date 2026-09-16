import { NavLink } from "react-router-dom";
import { FlaskConical, Calculator, Network, BarChart3, Beaker } from "lucide-react";

const links = [
  { to: "/",           label: "Home",           icon: FlaskConical, enabled: true  },
  { to: "/calculator", label: "Unit Calculator", icon: Calculator,   enabled: true  },
  { to: "/pfd",        label: "PFD Canvas",      icon: Network,      enabled: true },
  { to: "/utilities",  label: "Utilities",       icon: BarChart3,    enabled: false },
  { to: "/hc-recovery", label: "HC Recovery", icon: Beaker, enabled: true }
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">

        {/* Logo */}
        <NavLink
          to="/"
          className="flex items-center gap-2 text-green-800 font-semibold text-sm"
        >
          <span className="bg-green-700 text-white rounded-lg p-1.5">
            <FlaskConical size={15} />
          </span>
          ChE Sim
        </NavLink>

        {/* Links */}
        <nav className="flex items-center gap-1">
          {links.map(({ to, label, icon: Icon, enabled }) =>
            enabled ? (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors
                   ${isActive
                     ? "bg-green-50 text-green-800 font-medium"
                     : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                   }`
                }
              >
                <Icon size={14} />
                {label}
              </NavLink>
            ) : (
              <span
                key={to}
                title="Coming soon"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                           text-gray-400 cursor-not-allowed select-none"
              >
                <Icon size={14} />
                {label}
                <span className="text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium">
                  Soon
                </span>
              </span>
            )
          )}
        </nav>

      </div>
    </header>
  );
}
