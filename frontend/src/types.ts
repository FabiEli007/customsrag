export interface SourceRef {
  label: string;
  score: number;
}

export interface AskResponse {
  question: string;
  answer: string;
  sources: SourceRef[];
  latency_ms: number;
  mode: "generatif" | "extractif" | "aucun_resultat";
  language: "fr" | "en" | "mg";
}

export interface HealthResponse {
  status: string;
  index_loaded: boolean;
  documents_count: number;
  api_key_configured: boolean;
  model: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  latencyMs?: number;
  isError?: boolean;
  mode?: "generatif" | "extractif" | "aucun_resultat";
}
