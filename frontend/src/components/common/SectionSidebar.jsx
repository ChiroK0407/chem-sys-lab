/**
 * frontend/src/components/common/SectionSidebar.jsx
 *
 * Vertical list of section tabs used by both SectionedForm (inputs) and
 * SectionedResults (outputs). A section is:
 *   - "active"   — currently shown
 *   - "unlocked" — clickable, already saved (or results always unlocked)
 *   - "locked"   — not clickable yet; unlocks once the section above it
 *                  has been saved with valid values
 */

import { Lock, Check, Circle } from "lucide-react";

export default function SectionSidebar({ sections, activeId, unlockedIds, savedIds, onSelect }) {
  return (
    <div className="w-56 flex-shrink-0 space-y-1 pr-2 border-r border-gray-100">
      {sections.map((s, i) => {
        const isActive = s.id === activeId;
        const isUnlocked = unlockedIds.has(s.id);
        const isSaved = savedIds?.has(s.id);

        return (
          <button
            key={s.id}
            type="button"
            disabled={!isUnlocked}
            onClick={() => isUnlocked && onSelect(s.id)}
            className={`w-full flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors
              ${isActive
                ? "bg-brand-50 text-brand-700 font-medium border border-brand-200"
                : isUnlocked
                  ? "text-gray-600 hover:bg-gray-50 border border-transparent"
                  : "text-gray-300 border border-transparent cursor-not-allowed"
              }`}
          >
            <span className="flex-shrink-0">
              {!isUnlocked ? (
                <Lock size={13} />
              ) : isSaved ? (
                <Check size={13} className="text-green-600" />
              ) : (
                <Circle size={8} className={isActive ? "text-brand-500 fill-brand-500" : "text-gray-300 fill-gray-300"} />
              )}
            </span>
            <span className="flex-1">{s.label}</span>
            <span className="text-[10px] text-gray-300 font-mono">{i + 1}</span>
          </button>
        );
      })}
    </div>
  );
}
