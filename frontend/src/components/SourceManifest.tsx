import type { SourceRef } from "../types";
import { Icon } from "./Icon";

interface SourceManifestProps {
  entries: { source: SourceRef; questionIndex: number }[];
  eyebrow: string;
  title: string;
  emptyLabel: string;
  relevanceLabel: string;
}

/**
 * Panneau lateral listant les sources citees, dans l'esprit "Confidence
 * Indicators" / "Tariff Cards" du DESIGN.md : jauge de pertinence en or,
 * numero de reference en police tabulaire.
 */
export function SourceManifest({ entries, eyebrow, title, emptyLabel, relevanceLabel }: SourceManifestProps) {
  const maxScore = Math.max(1, ...entries.map((e) => e.source.score));

  return (
    <aside className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-5 flex flex-col gap-4 h-fit lg:sticky lg:top-6">
      <div className="border-b border-outline-variant pb-3">
        <p className="text-[10px] uppercase tracking-widest text-secondary font-bold">{eyebrow}</p>
        <h2 className="text-base font-semibold text-primary mt-0.5 flex items-center gap-2">
          <Icon name="folder_open" className="text-[18px]" />
          {title}
        </h2>
      </div>

      {entries.length === 0 ? (
        <p className="text-xs text-on-surface-variant leading-relaxed">{emptyLabel}</p>
      ) : (
        <ol className="flex flex-col gap-2.5 max-h-[60vh] overflow-y-auto">
          {entries.map((entry, i) => (
            <li
              key={i}
              className="rounded border border-outline-variant bg-surface p-3 flex flex-col gap-1.5"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-tabular text-[11px] font-semibold text-primary border border-primary rounded px-1.5 py-0.5 shrink-0">
                  N°{entry.questionIndex}
                </span>
                <span className="text-xs text-on-surface leading-snug text-right">{entry.source.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-surface-container-high overflow-hidden">
                  <div
                    className="h-full bg-secondary-container"
                    style={{ width: `${Math.min(100, (entry.source.score / maxScore) * 100)}%` }}
                  />
                </div>
                <span className="font-tabular text-[10px] text-on-surface-variant whitespace-nowrap">
                  {relevanceLabel} {entry.source.score.toFixed(1)}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
