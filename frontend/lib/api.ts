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
};

// Chat
export const chatApi = {
  send: (data: any) => apiFetch("/api/chat", { method: "POST", body: JSON.stringify(data) }),
  conversations: () => apiFetch("/api/conversations"),
  feedback: (msgId: string, data: any) =>
    apiFetch(`/api/messages/${msgId}/feedback`, { method: "POST", body: JSON.stringify(data) }),
};
