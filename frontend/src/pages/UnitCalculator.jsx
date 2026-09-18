import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Thermometer, Droplets, Activity, Layers, Combine, Split, FlaskConical, Wind, Columns3 } from "lucide-react";
import PageWrapper from "../components/layout/PageWrapper";
import HXForm from "../components/units/HXForm";
import HXResults from "../components/units/HXResults";
import PumpForm from "../components/units/PumpForm";
import PumpResults from "../components/units/PumpResults";
import MixerForm from "../components/units/MixerForm";
import MixerResults from "../components/units/MixerResults";
import SplitterForm from "../components/units/SplitterForm";
import SplitterResults from "../components/units/SplitterResults";
import CSTRForm from "../components/units/CSTRForm";
import PFRForm from "../components/units/PFRForm";
import ReactorResults from "../components/units/ReactorResults";
import AbsorberForm from "../components/units/AbsorberForm";
import StripperForm from "../components/units/StripperForm";
import AbsorberResults from "../components/units/AbsorberResults";
import DistillationForm from "../components/units/DistillationForm";
import DistillationResults from "../components/units/DistillationResults";

const UNITS = [
  { id: "heat-exchanger", label: "Heat Exchanger", icon: Thermometer, enabled: true },
  { id: "pump",           label: "Pump",           icon: Droplets,    enabled: true },
  { id: "mixer",    label: "Mixer",    icon: Combine, enabled: true },
  { id: "splitter", label: "Splitter", icon: Split,   enabled: true },
  { id: "cstr",     label: "CSTR",     icon: Activity, enabled: true },
  { id: "pfr",      label: "PFR",      icon: Layers,   enabled: true },
  { id: "absorber",  label: "Absorber",  icon: Wind,     enabled: true },
  { id: "stripper",  label: "Stripper",  icon: Droplets, enabled: true },
  { id: "distillation", label: "Distillation", icon: Columns3, enabled: true },
];

export default function UnitCalculator() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeUnit = searchParams.get("unit") ?? "heat-exchanger";
  const [result, setResult] = useState(null);

  function selectUnit(id) {
    setSearchParams({ unit: id });
    setResult(null);
  }

  return (
    <PageWrapper>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">Unit Calculator</h1>
        <p className="text-gray-500 text-sm">
          Solve individual unit operations. Select a unit, enter stream conditions, and solve.
        </p>
      </div>

      {/* Unit selector tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200 pb-0 flex-wrap">
        {UNITS.map(({ id, label, icon: Icon, enabled }) => (
          <button
            key={id}
            onClick={() => enabled && selectUnit(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors
              ${activeUnit === id
                ? "border-brand-600 text-brand-700"
                : enabled
                  ? "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  : "border-transparent text-gray-300 cursor-not-allowed"
              }`}
            disabled={!enabled}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Content — form left, results right on large screens */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Form */}
        <div>
          {activeUnit === "heat-exchanger" && (
            <HXForm onResult={setResult} />
          )}
          {activeUnit === "pump" && (
            <PumpForm onResult={setResult} />
          )}
          {activeUnit === "mixer" && (
            <MixerForm onResult={setResult} />
          )}
          {activeUnit === "splitter" && (
            <SplitterForm onResult={setResult} />
          )}
          {activeUnit === "cstr" && (
            <CSTRForm onResult={setResult} />
          )}
          {activeUnit === "pfr" && (
            <PFRForm onResult={setResult} />
          )}
          {activeUnit === "absorber" && (
            <AbsorberForm onResult={setResult} />
          )}
          {activeUnit === "stripper" && (
            <StripperForm onResult={setResult} />
          )}
          {activeUnit === "distillation" && (
            <DistillationForm onResult={setResult} />
          )}
        </div>

        {/* Results */}
        <div>
          {result ? (
            activeUnit === "heat-exchanger" ? (
              <HXResults result={result} />
            ) : activeUnit === "pump" ? (
              <PumpResults result={result} />
            ) : activeUnit === "mixer" ? (
              <MixerResults result={result} />
            ) : activeUnit === "splitter" ? (
              <SplitterResults result={result} />
            ) : activeUnit === "cstr" ? (
              <ReactorResults result={result} />
            ) : activeUnit === "pfr" ? (
              <ReactorResults result={result} />
            ) : activeUnit === "absorber" ? (
              // AbsorberResults renders both Absorber and Stripper output
              // (it branches internally on data.unit_type === "Stripper").
              <AbsorberResults result={result} />
            ) : activeUnit === "stripper" ? (
              <AbsorberResults result={result} />
            ) : activeUnit === "distillation" ? (
              <DistillationResults result={result} />
            ) : null
          ) : (
            <div className="rounded-xl border-2 border-dashed border-gray-200 p-12 text-center">
              <Thermometer size={32} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm font-medium text-gray-400">Results will appear here</p>
              <p className="text-xs text-gray-300 mt-1">Fill in the form and click Solve</p>
            </div>
          )}
        </div>

      </div>
    </PageWrapper>
  );
}
