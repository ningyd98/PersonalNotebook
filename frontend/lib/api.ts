const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Error class ──
export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

// ── Request interceptors ──
function buildHeaders(options?: RequestInit): HeadersInit {
  const headers: Record<string, string> = {};
  // Auto add Content-Type for JSON bodies
  if (options?.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  // Merge with existing headers
  if (options?.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((v, k) => { headers[k] = v; });
    } else if (Array.isArray(options.headers)) {
      options.headers.forEach(([k, v]) => { headers[k] = v; });
    } else {
      Object.assign(headers, options.headers);
    }
  }
  return headers;
}

// ── Core fetch with error handling ──
export async function apiFetch<T = any>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: buildHeaders(options),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Upload with FormData ──
export async function apiUpload(path: string, formData: FormData, options?: Omit<RequestInit, "body" | "headers">): Promise<any> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    ...options,
    body: formData,
    // Do NOT set Content-Type — browser sets it with boundary
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Create AbortController for cancellation ──
export function createCancellationToken() {
  return new AbortController();
}

// ── Knowledge Bases ──
export const kbApi = {
  list: (params?: Record<string, any>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return apiFetch(`/api/kbs${qs}`);
  },
  get: (id: string) => apiFetch(`/api/kbs/${id}`),
  create: (data: { name: string; description?: string; embedding_model?: string }) =>
    apiFetch("/api/kbs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: any) => apiFetch(`/api/kbs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => apiFetch(`/api/kbs/${id}`, { method: "DELETE" }),
};

// ── Documents ──
export const docApi = {
  list: (kbId: string, params?: Record<string, any>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return apiFetch(`/api/kbs/${kbId}/documents${qs}`);
  },
  get: (id: string) => apiFetch(`/api/documents/${id}`),
  delete: (id: string) => apiFetch(`/api/documents/${id}`, { method: "DELETE" }),
  reparse: (id: string) => apiFetch(`/api/documents/${id}/reparse`, { method: "POST" }),
  blocks: (id: string) => apiFetch(`/api/documents/${id}/blocks`),
  chunks: (id: string) => apiFetch(`/api/documents/${id}/chunks`),
  assets: (id: string) => apiFetch(`/api/documents/${id}/assets`),
  tables: (id: string) => apiFetch(`/api/documents/${id}/tables`),
  qualityReport: (id: string) => apiFetch(`/api/documents/${id}/quality-report`),
  reembed: (id: string) => apiFetch(`/api/documents/${id}/reembed`, { method: "POST" }),
  upload: (kbId: string, formData: FormData) => apiUpload(`/api/kbs/${kbId}/documents/upload`, formData),
};

// ── Chat ──
export const chatApi = {
  send: (data: any, signal?: AbortSignal) =>
    apiFetch("/api/chat", { method: "POST", body: JSON.stringify(data), signal }),
  debug: (data: any) => apiFetch("/api/chat/debug", { method: "POST", body: JSON.stringify(data) }),
  conversations: () => apiFetch("/api/conversations"),
  getConversation: (id: string) => apiFetch(`/api/conversations/${id}`),
  feedback: (msgId: string, data: any) =>
    apiFetch(`/api/messages/${msgId}/feedback`, { method: "POST", body: JSON.stringify(data) }),
};

// ── Evaluation ──
export const evalApi = {
  listSuites: () => apiFetch("/api/eval/suites"),
  getSuite: (id: string) => apiFetch(`/api/eval/suites/${id}`),
  createSuite: (data: any) => apiFetch("/api/eval/suites", { method: "POST", body: JSON.stringify(data) }),
  deleteSuite: (id: string) => apiFetch(`/api/eval/suites/${id}`, { method: "DELETE" }),
  listRuns: (suiteId?: string) => apiFetch(`/api/eval/runs${suiteId ? `?suite_id=${suiteId}` : ""}`),
  getRun: (id: string) => apiFetch(`/api/eval/runs/${id}`),
  startRun: (data: any) => apiFetch("/api/eval/runs", { method: "POST", body: JSON.stringify(data) }),
  listCases: (suiteId: string) => apiFetch(`/api/eval/suites/${suiteId}/cases`),
  createCase: (suiteId: string, data: any) =>
    apiFetch(`/api/eval/suites/${suiteId}/cases`, { method: "POST", body: JSON.stringify(data) }),
  importCases: (suiteId: string, data: any) =>
    apiFetch(`/api/eval/suites/${suiteId}/import`, { method: "POST", body: JSON.stringify(data) }),
  getReport: (runId: string) => apiFetch(`/api/eval/runs/${runId}/report`),
};

// ── Health ──
export const healthApi = {
  backend: () => apiFetch("/health"),
  modelGateway: () => {
    const gwUrl = process.env.NEXT_PUBLIC_MODEL_GATEWAY_URL || "http://localhost:8900";
    return fetch(`${gwUrl}/health`).then(r => r.json());
  },
  modelStatus: () => {
    const gwUrl = process.env.NEXT_PUBLIC_MODEL_GATEWAY_URL || "http://localhost:8900";
    return fetch(`${gwUrl}/model/status`).then(r => r.json());
  },
};
