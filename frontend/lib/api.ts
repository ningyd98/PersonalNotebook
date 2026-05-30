const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, options?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Knowledge Bases
export const kbApi = {
  list: () => apiFetch("/api/kbs"),
  get: (id: string) => apiFetch(`/api/kbs/${id}`),
  create: (data: any) => apiFetch("/api/kbs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: any) => apiFetch(`/api/kbs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => apiFetch(`/api/kbs/${id}`, { method: "DELETE" }),
};

// Documents
export const docApi = {
  list: (kbId: string) => apiFetch(`/api/kbs/${kbId}/documents`),
  get: (id: string) => apiFetch(`/api/documents/${id}`),
  delete: (id: string) => apiFetch(`/api/documents/${id}`, { method: "DELETE" }),
  reparse: (id: string) => apiFetch(`/api/documents/${id}/reparse`, { method: "POST" }),
  blocks: (id: string) => apiFetch(`/api/documents/${id}/blocks`),
  chunks: (id: string) => apiFetch(`/api/documents/${id}/chunks`),
  assets: (id: string) => apiFetch(`/api/documents/${id}/assets`),
  tables: (id: string) => apiFetch(`/api/documents/${id}/tables`),
  qualityReport: (id: string) => apiFetch(`/api/documents/${id}/quality-report`),
  reembed: (id: string) => apiFetch(`/api/documents/${id}/reembed`, { method: "POST" }),
};

// Chat
export const chatApi = {
  send: (data: any) => apiFetch("/api/chat", { method: "POST", body: JSON.stringify(data) }),
  conversations: () => apiFetch("/api/conversations"),
  feedback: (msgId: string, data: any) =>
    apiFetch(`/api/messages/${msgId}/feedback`, { method: "POST", body: JSON.stringify(data) }),
};

// Evaluation
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
};
