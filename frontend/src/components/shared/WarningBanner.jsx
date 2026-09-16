import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";

export default function WarningBanner({ warnings = [] }) {
  const [dismissed, setDismissed] = useState([]);
  const visible = warnings.filter((_, i) => !dismissed.includes(i));
  if (!visible.length) return null;

  return (
    <div className="space-y-2">
      {visible.map((w, i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-lg border border-amber-200
                     bg-amber-50 px-4 py-3"
        >
          <AlertTriangle size={15} className="text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-amber-800 flex-1">{w}</p>
          <button
            onClick={() => setDismissed((d) => [...d, warnings.indexOf(w)])}
            className="text-amber-500 hover:text-amber-700 flex-shrink-0"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
