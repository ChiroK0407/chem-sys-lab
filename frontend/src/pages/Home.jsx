import { useNavigate } from "react-router-dom";
import {
  FlaskConical, Thermometer, Zap, Droplets,
  ArrowRight, BookOpen, Network, GitBranch,
  Activity, Layers, Combine, Split,
} from "lucide-react";
import PageWrapper from "../components/layout/PageWrapper";

const UNITS = [
  {
    id: "heat-exchanger",
    name: "Heat Exchanger",
    icon: Thermometer,
    color: "bg-blue-50 text-blue-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "LMTD sizing and ε-NTU rating. Counterflow, parallel flow, shell & tube 1-2. Cooling water and steam utilities.",
    methods: ["LMTD", "ε-NTU", "F-factor"],
    ref: "C&R Vol.1 Ch.12",
    to: "/calculator?unit=heat-exchanger",
  },
  {
    id: "pump",
    name: "Pump",
    icon: Droplets,
    color: "bg-teal-50 text-teal-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "Head, NPSH, BEP, power draw. Centrifugal and positive displacement.",
    methods: ["Bernoulli", "Affinity laws"],
    ref: "C&R Vol.1 Ch.8",
    to: "/calculator?unit=pump",
  },
  {
    id: "mixer",
    name: "Mixer",
    icon: Combine,
    color: "bg-cyan-50 text-cyan-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "Mix two inlet streams into one outlet. Mass and energy balance for ideal mixing.",
    methods: ["Mass balance", "Energy balance"],
    ref: "C&R Vol.1 Ch.3",
    to: "/calculator?unit=mixer",
  },
  {
    id: "splitter",
    name: "Splitter",
    icon: Split,
    color: "bg-orange-50 text-orange-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "Split a feed stream across multiple outlets using split ratios.",
    methods: ["Split ratio", "Phase balance"],
    ref: "C&R Vol.1 Ch.3",
    to: "/calculator?unit=splitter",
  },
  {
    id: "cstr",
    name: "CSTR",
    icon: Activity,
    color: "bg-sky-50 text-sky-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "Continuous stirred-tank reactor sizing for conversion, volume, and heat duty.",
    methods: ["CSTR", "Energy balance"],
    ref: "Fogler Ch.5",
    to: "/calculator?unit=cstr",
  },
  {
    id: "pfr",
    name: "PFR",
    icon: Layers,
    color: "bg-cyan-50 text-cyan-600",
    badge: "Ready",
    badgeColor: "badge-green",
    description: "Plug flow reactor conversion and profile-based sizing.",
    methods: ["PFR", "Energy balance"],
    ref: "Fogler Ch.5",
    to: "/calculator?unit=pfr",
  },
  {
    id: "reactor",
    name: "Reactor",
    icon: FlaskConical,
    color: "bg-purple-50 text-purple-600",
    badge: "Soon",
    badgeColor: "badge-gray",
    description: "CSTR and PFR isothermal/adiabatic. Conversion, residence time, heat of reaction.",
    methods: ["Mole balance", "Energy balance"],
    ref: "Fogler Ch.5",
    to: null,
  },
  {
    id: "distillation",
    name: "Distillation",
    icon: GitBranch,
    color: "bg-amber-50 text-amber-600",
    badge: "Ready",
    badgeColor: "badge-gray",
    description: "FUG shortcut method. Number of stages, reflux ratio, condenser and reboiler duty.",
    methods: ["FUG", "McCabe-Thiele"],
    ref: "McCabe Ch.21",
    to: "/calculator?unit=distillation",
  },
];

const FEATURES = [
  {
    icon: BookOpen,
    title: "Transparent equations",
    desc: "Every calculation step logged. Traceable to Coulson & Richardson and McCabe, Smith & Harriott.",
  },
  {
    icon: Network,
    title: "Process networks",
    desc: "Connect units into full flowsheets. Sequential-modular solver propagates streams automatically.",
  },
  {
    icon: Zap,
    title: "Utility tracking",
    desc: "Cooling water demand, steam consumption, and power draw aggregated across the whole network.",
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div>
      {/* Hero */}
      <div className="border-b border-gray-200 bg-white">
        <PageWrapper>
          <div className="max-w-2xl py-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800 mb-4">
              <FlaskConical size={12} />
              First-principles process simulation
            </div>
            <h1 className="text-3xl font-semibold text-gray-900 mb-3">
              ChE Simulation Platform
            </h1>
            <p className="text-gray-500 text-base leading-relaxed mb-6">
              A lightweight, transparent simulation environment built for
              conceptual design and education. Every equation traceable to a textbook.
              No black boxes.
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate("/calculator?unit=heat-exchanger")}
                className="btn-primary"
              >
                Start with Heat Exchanger
                <ArrowRight size={15} />
              </button>
              <button className="btn-secondary" disabled title="Coming soon">
                Open PFD Canvas
              </button>
            </div>
          </div>
        </PageWrapper>
      </div>

      <PageWrapper>
        {/* Features */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-10">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-3">
              <div className="mt-0.5 flex-shrink-0 rounded-lg bg-brand-50 p-2 h-fit">
                <Icon size={16} className="text-brand-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900 mb-0.5">{title}</p>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Unit cards */}
        <div className="mb-3">
          <p className="section-title">Unit operations</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {UNITS.map((unit) => {
            const Icon = unit.icon;
            const isReady = unit.badge === "Ready";
            return (
              <div
                key={unit.id}
                onClick={() => isReady && unit.to && navigate(unit.to)}
                className={`card p-5 transition-all
                  ${isReady
                    ? "cursor-pointer hover:border-brand-300 hover:shadow-md"
                    : "opacity-60 cursor-not-allowed"
                  }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`rounded-xl p-2.5 ${unit.color}`}>
                    <Icon size={20} />
                  </div>
                  <span className={unit.badgeColor}>{unit.badge}</span>
                </div>

                <h3 className="font-semibold text-gray-900 mb-1">{unit.name}</h3>
                <p className="text-sm text-gray-500 leading-relaxed mb-3">{unit.description}</p>

                <div className="flex items-center justify-between">
                  <div className="flex gap-1.5 flex-wrap">
                    {unit.methods.map((m) => (
                      <span key={m} className="badge-blue text-[11px]">{m}</span>
                    ))}
                  </div>
                  <span className="text-xs text-gray-400">{unit.ref}</span>
                </div>

                {isReady && (
                  <div className="mt-4 pt-3 border-t border-gray-100 flex items-center text-sm font-medium text-brand-600">
                    Open calculator
                    <ArrowRight size={14} className="ml-1" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Philosophy footer */}
        <div className="mt-10 rounded-xl border border-gray-200 bg-gray-50 p-5">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Design philosophy
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm text-gray-600">
            <p>Steady-state only — no dynamic simulation. Every unit operation is an independent, modular object.</p>
            <p>Simplified thermodynamics using first-principles correlations from standard textbooks. No proprietary databases.</p>
            <p>Units take defined input streams and produce output streams. Multiple units connect to form process networks.</p>
          </div>
        </div>

      </PageWrapper>
    </div>
  );
}
