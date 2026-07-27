export type UiLanguage = "fr" | "en" | "mg";

export const UI_TRANSLATIONS: Record<UiLanguage, {
  countryLabel: string;
  appTitle: string;
  appSubtitle: string;
  statusConnecting: string;
  statusDocuments: (n: number) => string;
  emptyState: string;
  placeholder: string;
  submitButton: string;
  pendingMessage: string;
  manifestEyebrow: string;
  manifestTitle: string;
  manifestEmpty: string;
  relevance: string;
  warningIndex: string;
  warningKey: string;
  extractiveNote: string;
}> = {
  fr: {
    countryLabel: "Republique de Madagascar",
    appTitle: "CustomsRAG",
    appSubtitle: "Assistant reglementaire — Code des Douanes & Tarif des Douanes",
    statusConnecting: "connexion...",
    statusDocuments: (n) => `${n} textes indexes`,
    emptyState:
      "Posez une question sur un tarif, un code SH, une procedure ou une disposition du Code des Douanes, en francais, en anglais ou en malgache. Chaque reponse cite l'article ou le code exact utilise.",
    placeholder: "Ex : quel est le taux de droit de douane pour le fromage ?",
    submitButton: "Deposer la question",
    pendingMessage: "Consultation du registre...",
    manifestEyebrow: "Registre",
    manifestTitle: "Sources consultees",
    manifestEmpty: "Les articles et codes SH cites dans les reponses apparaitront ici, dans l'ordre de consultation.",
    relevance: "pertinence",
    warningIndex: "L'index n'est pas encore charge cote serveur. ",
    warningKey: "La cle ANTHROPIC_API_KEY n'est pas configuree cote serveur (mode extractif actif).",
    extractiveNote: "Reponse en mode extractif (sans generation IA)",
  },
  en: {
    countryLabel: "Republic of Madagascar",
    appTitle: "CustomsRAG",
    appSubtitle: "Regulatory assistant — Customs Code & Customs Tariff",
    statusConnecting: "connecting...",
    statusDocuments: (n) => `${n} indexed texts`,
    emptyState:
      "Ask a question about a tariff, an HS code, a procedure, or a provision of the Customs Code, in French, English, or Malagasy. Every answer cites the exact article or code used.",
    placeholder: "E.g.: what is the customs duty rate for cheese?",
    submitButton: "Submit question",
    pendingMessage: "Consulting the registry...",
    manifestEyebrow: "Registry",
    manifestTitle: "Sources consulted",
    manifestEmpty: "Articles and HS codes cited in answers will appear here, in consultation order.",
    relevance: "relevance",
    warningIndex: "The index is not loaded on the server yet. ",
    warningKey: "ANTHROPIC_API_KEY is not configured server-side (extractive mode active).",
    extractiveNote: "Answer in extractive mode (no AI generation)",
  },
  mg: {
    countryLabel: "Repoblikan'i Madagasikara",
    appTitle: "CustomsRAG",
    appSubtitle: "Mpanampy ara-panjakana — Fehezan-dalàna sy Tarifin'ny Fandintseranana",
    statusConnecting: "mifandray...",
    statusDocuments: (n) => `lahatsoratra ${n} voarakitra`,
    emptyState:
      "Anontanio ny momba ny tarifa, ny kaody SH, ny fombafomba na ny fepetra ao amin'ny Fehezan-dalàna momba ny Fandintseranana, amin'ny teny frantsay, anglisy na malagasy. Ny valiny rehetra dia manonona ny andininy na ny kaody nampiasaina.",
    placeholder: "Ohatra: firy ny hetra amin'ny fromazy?",
    submitButton: "Alefaso ny fanontaniana",
    pendingMessage: "Mijery ny rejisitra...",
    manifestEyebrow: "Rejisitra",
    manifestTitle: "Loharano nojerena",
    manifestEmpty: "Ny andininy sy kaody SH voatonona ao amin'ny valiny dia hiseho eto, araka ny filaharan'ny fandinihana.",
    relevance: "fifandraisana",
    warningIndex: "Mbola tsy voatahiry ny rejisitra eo amin'ny mpizara. ",
    warningKey: "Tsy voakasika ny ANTHROPIC_API_KEY eo amin'ny mpizara (fomba fanalana mihodina).",
    extractiveNote: "Valiny amin'ny fomba fanalana (tsy misy famoronana AI)",
  },
};
