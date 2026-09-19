/**
 * frontend/src/components/common/SectionedResults.jsx
 *
 * Read-only counterpart to SectionedForm — same title+dropdown switcher,
 * but results have no lock/save concept (everything's already computed),
 * so every section is unlocked as soon as a result exists. Each unit's
 * results component just supplies a schema of { id, label, render(result) }.
 */

import { useState } from "react";
import SectionSwitcher from "./SectionSwitcher";

export default function SectionedResults({ title = "Results", schema, result, initialActiveId }) {
  const available = schema.filter((s) => !s.isVisible || s.isVisible(result));
  const [activeId, setActiveId] = useState(initialActiveId ?? available[0]?.id);

  const section = available.find((s) => s.id === activeId) ?? available[0];
  if (!section) return null;

  const unlockedIds = new Set(available.map((s) => s.id));

  return (
    <div className="card p-5">
      <SectionSwitcher
        title={title}
        sections={available}
        activeId={section.id}
        unlockedIds={unlockedIds}
        savedIds={unlockedIds}
        onSelect={setActiveId}
      />
      <div className="space-y-4">
        {section.render(result)}
      </div>
    </div>
  );
}
