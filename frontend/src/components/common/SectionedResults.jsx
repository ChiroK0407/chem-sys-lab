/**
 * frontend/src/components/common/SectionedResults.jsx
 *
 * Read-only counterpart to SectionedForm — same sidebar pattern, but
 * results have no lock/save concept (everything's already computed), so
 * every section is unlocked as soon as a result exists. Each unit's
 * results component just supplies a schema of { id, label, render(result) }.
 */

import { useState } from "react";
import SectionSidebar from "./SectionSidebar";

export default function SectionedResults({ schema, result, initialActiveId }) {
  const available = schema.filter((s) => !s.isVisible || s.isVisible(result));
  const [activeId, setActiveId] = useState(initialActiveId ?? available[0]?.id);

  const section = available.find((s) => s.id === activeId) ?? available[0];
  if (!section) return null;

  const unlockedIds = new Set(available.map((s) => s.id));

  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex">
        <div className="p-4">
          <SectionSidebar
            sections={available}
            activeId={section.id}
            unlockedIds={unlockedIds}
            savedIds={unlockedIds}
            onSelect={setActiveId}
          />
        </div>
        <div className="flex-1 p-5 min-w-0 space-y-4">
          {section.render(result)}
        </div>
      </div>
    </div>
  );
}
