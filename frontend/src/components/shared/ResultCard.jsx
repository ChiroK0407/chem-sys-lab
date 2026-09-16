export default function ResultCard({
  label,
  value,
  unit,
  highlight = false,
  warn = false,
}) {
  return (
    <div
      className={`rounded-xl border p-4 transition-colors
        ${warn
          ? "border-amber-200 bg-amber-50"
          : highlight
            ? "border-green-200 bg-green-50"
            : "border-gray-200 bg-white"
        }`}
    >
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p
        className={`text-2xl font-semibold tracking-tight
          ${warn
            ? "text-amber-800"
            : highlight
              ? "text-green-800"
              : "text-gray-900"
          }`}
      >
        {value ?? "—"}
      </p>
      {unit && <p className="text-xs text-gray-400 mt-0.5">{unit}</p>}
    </div>
  );
}
