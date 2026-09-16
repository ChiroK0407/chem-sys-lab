import { useState } from "react";
import { ChevronDown, ChevronUp, BookOpen, Download } from "lucide-react";

export default function CalcLog({ log = [], unitId = "unit" }) {
  const [open, setOpen] = useState(false);
  if (!log.length) return null;

  function handleDownload() {
    const timestamp = new Date()
      .toISOString()
      .replace(/[:.]/g, "-")
      .slice(0, 19);

    const header = [
      "ChE Simulation Platform — Calculation Log",
      `Unit: ${unitId}`,
      `Generated: ${new Date().toLocaleString()}`,
      "=".repeat(55),
      "",
    ].join("\n");

    const body = log.join("\n");
    const blob = new Blob([header + body], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href     = url;
    a.download = `calc-log_${unitId}_${timestamp}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">

      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50">

        {/* Toggle */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700
                     hover:text-gray-900 transition-colors"
        >
          <BookOpen size={15} className="text-green-700" />
          Step-by-step working
          <span className="inline-flex items-center rounded-full px-2.5 py-0.5
                           text-xs font-medium bg-gray-100 text-gray-600">
            {log.length} steps
          </span>
          {open
            ? <ChevronUp   size={15} className="text-gray-400 ml-1" />
            : <ChevronDown size={15} className="text-gray-400 ml-1" />
          }
        </button>

        {/* Download button — always visible */}
        <button
          onClick={handleDownload}
          title="Download calculation log as .txt"
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300
                     bg-white px-3 py-1.5 text-xs font-medium text-gray-600
                     hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <Download size={13} />
          Download log
        </button>

      </div>

      {/* Log body */}
      {open && (
        <div className="bg-white border-t border-gray-100 px-4 py-3
                        max-h-96 overflow-y-auto">
          {log.map((line, i) => (
            <p key={i} className="font-mono text-xs leading-6 text-gray-700
                                  whitespace-pre-wrap">
              {line || "\u00A0"}
            </p>
          ))}
        </div>
      )}

    </div>
  );
}
