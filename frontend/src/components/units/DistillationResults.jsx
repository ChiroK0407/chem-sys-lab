import { Flame, Snowflake, GitBranch } from "lucide-react";
import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";
import SectionedResults from "../common/SectionedResults";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function fmt(v, dp = 2) { return v == null ? "—" : Number(v).toFixed(dp); }

function CompTable({ title, comp }) {
  if (!comp) return null;
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-2">{title}</p>
      <table className="w-full">
        <thead><tr className="border-b border-gray-100">
          <th className="text-left text-xs text-gray-400 pb-1">Component</th>
          <th className="text-right text-xs text-gray-400 pb-1">Mole fraction</th>
        </tr></thead>
        <tbody>
          {Object.entries(comp).map(([name, x]) => (
            <tr key={name} className="border-b border-gray-50 last:border-0">
              <td className="py-1 text-sm text-gray-700">{name}</td>
              <td className="py-1 text-sm text-right font-mono text-gray-800">{fmt(x, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function McCabeThieleChart({ mc }) {
  if (!mc) return null;
  const eqData  = mc.equilibrium.map(([x,y]) => ({ x, y_eq: y }));
  const rectData = mc.op_rect.map(([x,y])  => ({ x, y_rect: y }));
  const stripData= mc.op_strip.map(([x,y]) => ({ x, y_strip: y }));
  const stageData= mc.stages.map(([x,y])   => ({ x, y_stage: y }));

  const allX = [...new Set([
    ...eqData.map(d=>d.x), ...rectData.map(d=>d.x),
    ...stripData.map(d=>d.x), ...stageData.map(d=>d.x)
  ])].sort((a,b)=>a-b);

  const merged = allX.map(x => {
    const eq    = eqData.find(d=>Math.abs(d.x-x)<0.001);
    const rect  = rectData.find(d=>Math.abs(d.x-x)<0.001);
    const strip = stripData.find(d=>Math.abs(d.x-x)<0.001);
    const stage = stageData.find(d=>Math.abs(d.x-x)<0.001);
    return {
      x: parseFloat(x.toFixed(4)),
      eq: eq?.y_eq, diag: x, rect: rect?.y_rect, strip: strip?.y_strip, stage: stage?.y_stage,
    };
  });

  return (
    <div>
      <p className="text-xs text-gray-400 mb-3">
        {mc.n_stages_mt} theoretical stages  |  Feed stage {mc.feed_stage_mt} from top
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={merged} margin={{ top:5, right:20, bottom:20, left:10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="x" label={{ value:"x (liquid)", position:"insideBottom", offset:-10, fontSize:11 }} tick={{fontSize:11}} domain={[0,1]} />
          <YAxis label={{ value:"y (vapour)", angle:-90, position:"insideLeft", fontSize:11 }} tick={{fontSize:11}} domain={[0,1]} />
          <Tooltip formatter={(v)=>v!=null?v.toFixed(4):null} />
          <Legend wrapperStyle={{fontSize:11}} />
          <Line type="monotone" dataKey="eq"    stroke="#3b6d11" dot={false} strokeWidth={2} name="Equilibrium" />
          <Line type="monotone" dataKey="diag"  stroke="#9ca3af" dot={false} strokeWidth={1} strokeDasharray="4 4" name="y=x" />
          <Line type="monotone" dataKey="rect"  stroke="#2563eb" dot={false} strokeWidth={1.5} name="Rect. op. line" />
          <Line type="monotone" dataKey="strip" stroke="#d97706" dot={false} strokeWidth={1.5} name="Strip. op. line" />
          <Line type="monotone" dataKey="stage" stroke="#dc2626" dot={false} strokeWidth={1} name="Stages" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

const RESULT_SCHEMA = [
  {
    id: "overview",
    label: "Overview",
    render: (result) => (
      <>
        <WarningBanner warnings={result.warnings} />
        <div className="flex items-center gap-3 px-1">
          <div className="rounded-xl bg-blue-50 border border-blue-200 p-2"><GitBranch size={18} className="text-blue-600" /></div>
          <div>
            <p className="text-sm font-semibold text-gray-900">{result.unit_id} — {result.n_components} components</p>
            <p className="text-xs text-gray-500">
              R/R_min = {result.R_Rmin_ratio}  |  η_tray = {result.tray_efficiency}  |  {result.condenser_type} condenser
            </p>
          </div>
        </div>
      </>
    ),
  },
  {
    id: "stages",
    label: "Stage Counts & Flows",
    render: (result) => (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ResultCard label="N_min (Fenske)"    value={fmt(result.N_min)}          unit="stages" />
          <ResultCard label="R_min (Underwood)" value={fmt(result.R_min, 4)}       unit="—" />
          <ResultCard label="R operating"       value={fmt(result.R_operating, 4)} unit="—" highlight />
          <ResultCard label="N theoretical"     value={fmt(result.N_theoretical)}  unit="stages" />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ResultCard label="N actual"    value={result.N_actual}        unit="trays" highlight />
          <ResultCard label="Feed stage"  value={result.feed_stage}      unit="from top" />
          <ResultCard label="Distillate D" value={fmt(result.D_mol_s, 3)} unit="mol/s" />
          <ResultCard label="Bottoms B"    value={fmt(result.B_mol_s, 3)} unit="mol/s" />
        </div>
      </>
    ),
  },
  {
    id: "duties",
    label: "Duties",
    render: (result) => (
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 flex items-start gap-3">
          <div className="rounded-lg bg-blue-100 p-1.5"><Snowflake size={16} className="text-blue-600" /></div>
          <div>
            <p className="text-xs font-medium text-blue-800">Condenser (cooling)</p>
            <p className="text-xl font-semibold text-blue-900">{fmt(result.Q_condenser_kW, 1)} kW</p>
          </div>
        </div>
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-4 flex items-start gap-3">
          <div className="rounded-lg bg-orange-100 p-1.5"><Flame size={16} className="text-orange-600" /></div>
          <div>
            <p className="text-xs font-medium text-orange-800">Reboiler (heating)</p>
            <p className="text-xl font-semibold text-orange-900">{fmt(result.Q_reboiler_kW, 1)} kW</p>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "compositions",
    label: "Product Compositions",
    render: (result) => (
      <div className="grid grid-cols-2 gap-6">
        <CompTable title="Distillate" comp={result.distillate_composition} />
        <CompTable title="Bottoms"    comp={result.bottoms_composition} />
      </div>
    ),
  },
  {
    id: "mccabe-thiele",
    label: "McCabe-Thiele Diagram",
    isVisible: (result) => !!result.mccabe_thiele,
    render: (result) => <McCabeThieleChart mc={result.mccabe_thiele} />,
  },
  {
    id: "log",
    label: "Calculation Log",
    isVisible: (result) => !!(result.calculation_log && result.calculation_log.length),
    render: (result) => <CalcLog log={result.calculation_log} unitId={result.unit_id} />,
  },
];

export default function DistillationResults({ result }) {
  if (!result) return null;
  return <SectionedResults schema={RESULT_SCHEMA} result={result} />;
}
