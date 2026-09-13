import { useEffect, useState } from "react";
import { api } from "./api";

function AuthForm({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "signup") {
        await api.signup({ username: form.username, email: form.email, password: form.password });
      }
      await api.login({ username: form.username, password: form.password });
      onAuthed();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h2>{mode === "login" ? "Log in" : "Sign up"}</h2>
      <form onSubmit={submit}>
        <input
          placeholder="username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        {mode === "signup" && (
          <input
            placeholder="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        )}
        <input
          placeholder="password"
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <button type="submit">{mode === "login" ? "Log in" : "Sign up"}</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <button onClick={() => setMode(mode === "login" ? "signup" : "login")}>
        Switch to {mode === "login" ? "signup" : "login"}
      </button>
    </div>
  );
}

function CommunitiesView({ onSelect }) {
  const [communities, setCommunities] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  function refresh() {
    api.listCommunities().then(setCommunities).catch((err) => setError(err.message));
  }

  useEffect(refresh, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createCommunity({ name });
      setName("");
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h2>Communities</h2>
      <form onSubmit={create}>
        <input placeholder="new community name" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit">Create</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <ul>
        {communities.map((c) => (
          <li key={c.id}>
            <button onClick={() => onSelect(c)}>{c.name}</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PostsView({ community, onBack }) {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 });
  const [form, setForm] = useState({ title: "", content: "" });
  const [error, setError] = useState("");

  function load(page = 1) {
    api
      .listPosts(community.id, page)
      .then(setData)
      .catch((err) => setError(err.message));
  }

  useEffect(() => load(1), [community.id]);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createPost(community.id, form);
      setForm({ title: "", content: "" });
      load(1);
    } catch (err) {
      setError(err.message);
    }
  }

  const totalPages = Math.ceil(data.total / data.page_size) || 1;

  return (
    <div>
      <button onClick={onBack}>&larr; back to communities</button>
      <h2>{community.name}</h2>
      <form onSubmit={create}>
        <input placeholder="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <input
          placeholder="content"
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
        />
        <button type="submit">Post</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <ul>
        {data.items.map((p) => (
          <li key={p.id}>
            <strong>{p.title}</strong> — {p.content}
          </li>
        ))}
      </ul>
      <p>
        Page {data.page} of {totalPages} ({data.total} posts total)
      </p>
      <button disabled={data.page <= 1} onClick={() => load(data.page - 1)}>
        Prev
      </button>
      <button disabled={data.page >= totalPages} onClick={() => load(data.page + 1)}>
        Next
      </button>
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.isLoggedIn());
  const [community, setCommunity] = useState(null);

  if (!loggedIn) return <AuthForm onAuthed={() => setLoggedIn(true)} />;

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={() => {
            api.logout();
            setLoggedIn(false);
            setCommunity(null);
          }}
        >
          Logout
        </button>
      </div>

      {!community && <CommunitiesView onSelect={setCommunity} />}
      {community && <PostsView community={community} onBack={() => setCommunity(null)} />}
    </div>
  );
}
