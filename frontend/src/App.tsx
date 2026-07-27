import { useEffect, useRef, useState } from "react";
import { askQuestion, fetchHealth, ApiError } from "./api";
import type { ChatMessage, HealthResponse, SourceRef } from "./types";
import { MessageBubble } from "./components/MessageBubble";
import { QuestionInput } from "./components/QuestionInput";
import { SourceManifest } from "./components/SourceManifest";
import { Icon } from "./components/Icon";
import { UI_TRANSLATIONS, type UiLanguage } from "./i18n";

let messageIdCounter = 0;
function nextId(): string {
  messageIdCounter += 1;
  return `msg-${messageIdCounter}`;
}

const LANGUAGE_OPTIONS: { code: UiLanguage; label: string }[] = [
  { code: "fr", label: "FR" },
  { code: "en", label: "EN" },
  { code: "mg", label: "MG" },
];

export default function App() {
  const [uiLang, setUiLang] = useState<UiLanguage>("fr");
  const t = UI_TRANSLATIONS[uiLang];

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [manifestEntries, setManifestEntries] = useState<
    { source: SourceRef; questionIndex: number }[]
  >([]);
  const questionCount = useRef(0);
  const scrollAnchor = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleAsk(question: string) {
    questionCount.current += 1;
    const currentQuestionIndex = questionCount.current;

    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: question }]);
    setPending(true);

    try {
      const result = await askQuestion(question);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          latencyMs: result.latency_ms,
          mode: result.mode,
        },
      ]);
      if (result.sources.length > 0) {
        setManifestEntries((prev) => [
          ...prev,
          ...result.sources.map((source) => ({ source, questionIndex: currentQuestionIndex })),
        ]);
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Le service est momentanement injoignable. Reessayez dans un instant.";
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "assistant", content: message, isError: true },
      ]);
    } finally {
      setPending(false);
    }
  }

  const indexUnavailable = health !== null && !health.index_loaded;
  const keyMissing = health !== null && !health.api_key_configured;

  return (
    <div className="min-h-screen flex flex-col bg-surface-bright">
      {/* TopAppBar */}
      <header className="w-full border-b border-outline-variant bg-surface-bright">
        <div className="flex items-center justify-between px-4 md:px-8 h-16 max-w-[1440px] mx-auto">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-9 h-9 rounded bg-primary text-on-primary">
              <Icon name="gavel" />
            </span>
            <div className="leading-tight">
              <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-semibold">
                {t.countryLabel}
              </p>
              <h1 className="text-lg font-bold text-primary tracking-tight">{t.appTitle}</h1>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex rounded border border-outline-variant overflow-hidden">
              {LANGUAGE_OPTIONS.map((opt) => (
                <button
                  key={opt.code}
                  type="button"
                  onClick={() => setUiLang(opt.code)}
                  className={`px-2.5 py-1 text-xs font-semibold tracking-wide transition-colors ${
                    opt.code === uiLang
                      ? "bg-primary text-on-primary"
                      : "bg-surface text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-on-surface-variant font-tabular">
              <span
                className={`w-2 h-2 rounded-full ${
                  health?.status === "ok" ? "bg-success" : "bg-secondary-container"
                }`}
              />
              {health ? t.statusDocuments(health.documents_count) : t.statusConnecting}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-grow w-full max-w-[1440px] mx-auto px-4 md:px-8 py-6 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-6">
        <section className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col overflow-hidden">
          {(indexUnavailable || keyMissing) && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-secondary-container/40 border-b border-outline-variant text-sm text-on-secondary-container">
              <Icon name="info" className="text-[18px]" />
              <span>
                {indexUnavailable && t.warningIndex}
                {keyMissing && t.warningKey}
              </span>
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 md:px-6 py-5 flex flex-col gap-4 min-h-[50vh] max-h-[65vh]">
            {messages.length === 0 && (
              <div className="m-auto max-w-md text-center text-on-surface-variant text-sm leading-relaxed">
                <Icon name="forum" className="text-[32px] text-primary-fixed-dim mb-2" />
                <p>{t.emptyState}</p>
              </div>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} extractiveNote={t.extractiveNote} relevanceLabel={t.relevance} />
            ))}
            {pending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-lg border border-dashed border-outline-variant px-4 py-2.5 text-xs text-on-surface-variant font-tabular">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed-dim animate-pulse" />
                  {t.pendingMessage}
                </div>
              </div>
            )}
            <div ref={scrollAnchor} />
          </div>

          <QuestionInput onSubmit={handleAsk} disabled={pending} placeholder={t.placeholder} submitLabel={t.submitButton} />
        </section>

        <SourceManifest
          entries={manifestEntries}
          eyebrow={t.manifestEyebrow}
          title={t.manifestTitle}
          emptyLabel={t.manifestEmpty}
          relevanceLabel={t.relevance}
        />
      </main>
    </div>
  );
}
