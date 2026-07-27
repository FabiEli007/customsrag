import type { ChatMessage } from "../types";
import { Icon } from "./Icon";

interface MessageBubbleProps {
  message: ChatMessage;
  extractiveNote: string;
  relevanceLabel: string;
}

export function MessageBubble({ message, extractiveNote }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70ch] rounded-lg rounded-tr-none bg-primary text-on-primary px-4 py-2.5 text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        className={`max-w-[70ch] rounded-lg rounded-tl-none border px-4 py-3 text-sm leading-relaxed ${
          message.isError
            ? "border-error-container bg-error-container/30 text-on-error-container italic"
            : "border-outline-variant bg-surface"
        }`}
      >
        {!message.isError && message.mode === "extractif" && (
          <div className="inline-flex items-center gap-1 mb-2 px-2 py-0.5 rounded bg-secondary-container/60 text-on-secondary-container text-[11px] font-semibold uppercase tracking-wide">
            <Icon name="bolt" className="text-[14px]" />
            {extractiveNote}
          </div>
        )}
        <p className="whitespace-pre-wrap text-on-surface">{message.content}</p>

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {message.sources.map((s, i) => (
              <span
                key={i}
                className="font-tabular text-[11px] bg-surface-container-high border border-outline-variant text-on-surface-variant px-2 py-0.5 rounded"
              >
                {s.label}
              </span>
            ))}
          </div>
        )}

        {message.latencyMs !== undefined && (
          <div className="font-tabular text-[10px] text-on-surface-variant mt-2">{message.latencyMs} ms</div>
        )}
      </div>
    </div>
  );
}
