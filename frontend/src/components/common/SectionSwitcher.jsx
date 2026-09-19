/**
 * frontend/src/components/common/SectionSwitcher.jsx
 *
 * Replaces the vertical SectionSidebar with a single row:
 *   [ Title (left) ]                                   [ dropdown (right) ]
 * Selecting a section from the dropdown swaps the content below it, which
 * now gets the full panel width instead of sharing it with a sidebar
 * column. Locked sections (form use case) render as disabled <option>s —
 * native <select> handles that (and mobile/keyboard) for free.
 */

export default function SectionSwitcher({ title, sections, activeId, unlockedIds, savedIds, onSelect }) {
  const activeIndex = sections.findIndex((s) => s.id === activeId);

  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
        {sections.length > 1 && (
          <span className="ml-2 font-normal normal-case text-gray-300">
            Step {activeIndex + 1} of {sections.length}
          </span>
        )}
      </p>
      <select
        className="select w-64"
        value={activeId}
        onChange={(e) => onSelect(e.target.value)}
      >
        {sections.map((s) => {
          const locked = !unlockedIds.has(s.id);
          const saved = savedIds?.has(s.id);
          const prefix = locked ? "🔒 " : saved ? "✓ " : "";
          return (
            <option key={s.id} value={s.id} disabled={locked}>
              {prefix}{s.label}
            </option>
          );
        })}
      </select>
    </div>
  );
}
