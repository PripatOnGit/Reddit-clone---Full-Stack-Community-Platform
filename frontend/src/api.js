const API_BASE = "http://localhost:8000";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(API_BASE + path, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  signup: (data) => apiFetch("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: async (data) => {
    const result = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify(data) });
    localStorage.setItem("access_token", result.access_token);
    return result;
  },
  logout: () => localStorage.removeItem("access_token"),
  isLoggedIn: () => !!localStorage.getItem("access_token"),

  listCommunities: () => apiFetch("/communities"),
  createCommunity: (data) => apiFetch("/communities", { method: "POST", body: JSON.stringify(data) }),

  listPosts: (communityId, page = 1) => apiFetch(`/communities/${communityId}/posts?page=${page}`),
  createPost: (communityId, data) =>
    apiFetch(`/communities/${communityId}/posts`, { method: "POST", body: JSON.stringify(data) }),
};
