import { useState, useRef, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --ink: #0f0e0c;
    --paper: #f5f0e8;
    --cream: #ede7d9;
    --gold: #b8923a;
    --gold-light: #d4a85a;
    --muted: #7a7168;
    --rule: #d4ccbc;
    --card-bg: #faf7f2;
  }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
  }

  .grain {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 100;
    opacity: 0.035;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-size: 128px;
  }

  .shell {
    max-width: 720px;
    margin: 0 auto;
    padding: 0 24px 80px;
  }

  /* ── Header ── */
  .header {
    padding: 56px 0 40px;
    border-bottom: 1px solid var(--rule);
    margin-bottom: 48px;
  }

  .eyebrow {
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 12px;
  }

  .logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 52px;
    font-weight: 300;
    line-height: 1;
    letter-spacing: -0.01em;
    color: var(--ink);
  }

  .logo em {
    font-style: italic;
    color: var(--gold);
  }

  .tagline {
    margin-top: 10px;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.08em;
  }

  /* ── Input area ── */
  .input-block {
    margin-bottom: 40px;
  }

  .input-label {
    display: block;
    font-size: 10px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
  }

  .brief-wrap {
    position: relative;
  }

  .brief-input {
    width: 100%;
    background: var(--card-bg);
    border: 1px solid var(--rule);
    border-bottom: 2px solid var(--ink);
    padding: 16px 16px 48px;
    font-family: 'Cormorant Garamond', serif;
    font-size: 18px;
    font-weight: 400;
    color: var(--ink);
    resize: none;
    outline: none;
    min-height: 100px;
    transition: border-color 0.2s;
    line-height: 1.6;
  }

  .brief-input::placeholder {
    color: var(--muted);
    font-style: italic;
  }

  .brief-input:focus {
    border-color: var(--rule);
    border-bottom-color: var(--gold);
  }

  .submit-btn {
    position: absolute;
    bottom: 12px;
    right: 12px;
    background: var(--ink);
    color: var(--paper);
    border: none;
    padding: 8px 20px;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
  }

  .submit-btn:hover:not(:disabled) {
    background: var(--gold);
    transform: translateY(-1px);
  }

  .submit-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  /* ── Loading ── */
  .loading {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.08em;
    padding: 24px 0;
  }

  .dots span {
    animation: blink 1.2s infinite;
    opacity: 0;
  }
  .dots span:nth-child(2) { animation-delay: 0.2s; }
  .dots span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes blink {
    0%, 80%, 100% { opacity: 0; }
    40% { opacity: 1; }
  }

  /* ── Error ── */
  .error-box {
    border: 1px solid #c0392b;
    padding: 14px 16px;
    font-size: 12px;
    color: #c0392b;
    margin-bottom: 32px;
    letter-spacing: 0.04em;
  }

  /* ── Stats bar ── */
  .stats-bar {
    display: flex;
    gap: 32px;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    padding: 12px 0;
    margin-bottom: 36px;
    opacity: 0;
    animation: fadein 0.4s 0.1s forwards;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .stat-label {
    font-size: 9px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
  }

  .stat-val {
    font-family: 'Cormorant Garamond', serif;
    font-size: 22px;
    font-weight: 300;
    color: var(--ink);
  }

  .stat-val.gold { color: var(--gold); }

  /* ── Profile pill row ── */
  .profile-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 36px;
    opacity: 0;
    animation: fadein 0.4s 0.15s forwards;
  }

  .pill {
    font-size: 10px;
    letter-spacing: 0.06em;
    border: 1px solid var(--rule);
    padding: 4px 10px;
    color: var(--muted);
    background: var(--cream);
  }

  .pill strong {
    color: var(--ink);
    font-weight: 400;
  }

  /* ── Section heading ── */
  .section-head {
    font-size: 9px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 20px;
    opacity: 0;
    animation: fadein 0.4s 0.2s forwards;
  }

  /* ── Venue cards ── */
  .cards {
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin-bottom: 48px;
  }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--rule);
    padding: 24px 24px 20px;
    opacity: 0;
    transform: translateY(8px);
    animation: slideup 0.35s forwards;
    position: relative;
    overflow: hidden;
  }

  .card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--rule);
    transition: background 0.2s;
  }

  .card:hover::before { background: var(--gold); }

  .card:nth-child(1) { animation-delay: 0.25s; }
  .card:nth-child(2) { animation-delay: 0.35s; }
  .card:nth-child(3) { animation-delay: 0.45s; }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .venue-name {
    font-family: 'Cormorant Garamond', serif;
    font-size: 26px;
    font-weight: 400;
    line-height: 1.1;
    color: var(--ink);
  }

  .score-badge {
    font-size: 11px;
    font-weight: 400;
    letter-spacing: 0.06em;
    color: var(--gold);
    border: 1px solid var(--gold-light);
    padding: 3px 10px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-left: 16px;
    margin-top: 4px;
  }

  .rationale {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.65;
    letter-spacing: 0.01em;
  }

  /* ── Explanation ── */
  .explanation-block {
    border-top: 1px solid var(--rule);
    padding-top: 32px;
    margin-bottom: 48px;
    opacity: 0;
    animation: fadein 0.5s 0.6s forwards;
  }

  .explanation-text {
    font-family: 'Cormorant Garamond', serif;
    font-size: 17px;
    font-weight: 300;
    line-height: 1.8;
    color: var(--ink);
    white-space: pre-wrap;
  }

  .explanation-text strong {
    font-weight: 600;
    color: var(--ink);
  }

  /* ── Refine ── */
  .refine-block {
    border-top: 1px solid var(--rule);
    padding-top: 32px;
    opacity: 0;
    animation: fadein 0.4s 0.7s forwards;
  }

  .refine-label {
    font-size: 9px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 12px;
  }

  .refine-row {
    display: flex;
    gap: 0;
  }

  .refine-input {
    flex: 1;
    background: var(--card-bg);
    border: 1px solid var(--rule);
    border-right: none;
    padding: 10px 14px;
    font-family: 'Cormorant Garamond', serif;
    font-size: 16px;
    color: var(--ink);
    outline: none;
    transition: border-color 0.2s;
  }

  .refine-input::placeholder {
    color: var(--muted);
    font-style: italic;
  }

  .refine-input:focus { border-color: var(--gold); }

  .refine-btn {
    background: var(--ink);
    color: var(--paper);
    border: 1px solid var(--ink);
    padding: 10px 18px;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    transition: background 0.15s;
    white-space: nowrap;
  }

  .refine-btn:hover:not(:disabled) { background: var(--gold); border-color: var(--gold); }
  .refine-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .reset-link {
    display: inline-block;
    margin-top: 16px;
    font-size: 10px;
    letter-spacing: 0.08em;
    color: var(--muted);
    text-decoration: underline;
    cursor: pointer;
    background: none;
    border: none;
    font-family: 'DM Mono', monospace;
  }

  .reset-link:hover { color: var(--ink); }

  /* ── Animations ── */
  @keyframes fadein {
    to { opacity: 1; }
  }

  @keyframes slideup {
    to { opacity: 1; transform: translateY(0); }
  }
`;

function renderExplanation(text) {
  // Bold **Venue Name** patterns
  return text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

export default function App() {
  const [brief, setBrief] = useState("");
  const [refineText, setRefineText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const resultsRef = useRef(null);

  useEffect(() => {
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
    return () => document.head.removeChild(style);
  }, []);

  useEffect(() => {
    if (result && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  async function handleMatch() {
    if (!brief.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${API}/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: brief.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefine() {
    if (!refineText.trim() || !result?.thread_id) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: result.thread_id, refinement: refineText.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setResult(await res.json());
      setRefineText("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setBrief("");
    setRefineText("");
    setError("");
  }

  return (
    <>
      <div className="grain" />
      <div className="shell">
        <header className="header">
          <p className="eyebrow">Boston · AI-Native</p>
          <h1 className="logo">Venu<em>Match</em></h1>
          <p className="tagline">describe your event. find your venue.</p>
        </header>

        <div className="input-block">
          <label className="input-label">Your Event Brief</label>
          <div className="brief-wrap">
            <textarea
              className="brief-input"
              rows={4}
              placeholder="Birthday dinner for 25. Hidden gem — speakeasy vibe, moody atmosphere. ~$2,000 budget."
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleMatch();
              }}
            />
            <button
              className="submit-btn"
              onClick={handleMatch}
              disabled={loading || !brief.trim()}
            >
              {loading && !result ? "Finding..." : "Find Venues"}
            </button>
          </div>
        </div>

        {loading && !result && (
          <div className="loading">
            <span>Filtering venues</span>
            <span className="dots">
              <span>.</span><span>.</span><span>.</span>
            </span>
          </div>
        )}

        {error && <div className="error-box">{error}</div>}

        {result && (
          <div ref={resultsRef}>
            {/* Stats */}
            <div className="stats-bar">
              <div className="stat">
                <span className="stat-label">Venues Matched</span>
                <span className="stat-val">{result.passing_count}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Top Picks</span>
                <span className="stat-val">{result.top3.length}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Budget</span>
                <span className="stat-val">
                  ${result.profile.budget_per_person}
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>/pp</span>
                </span>
              </div>
              {result.budget_widened && (
                <div className="stat">
                  <span className="stat-label">Note</span>
                  <span className="stat-val gold" style={{ fontSize: 14, marginTop: 4 }}>Budget widened +20%</span>
                </div>
              )}
            </div>

            {/* Profile pills */}
            <div className="profile-row">
              <span className="pill"><strong>{result.profile.occasion}</strong></span>
              <span className="pill">guests: <strong>{result.profile.headcount}</strong></span>
              {result.profile.neighborhood_pref?.length > 0 && (
                <span className="pill">{result.profile.neighborhood_pref.join(", ")}</span>
              )}
              <span className="pill" style={{ fontStyle: "italic", fontFamily: "Cormorant Garamond, serif", fontSize: 12 }}>
                {result.profile.vibe_signals}
              </span>
            </div>

            {/* Cards */}
            <p className="section-head">Top Matches</p>
            <div className="cards">
              {result.top3.map((v) => (
                <div className="card" key={v.venue_id}>
                  <div className="card-top">
                    <span className="venue-name">{v.venue_name}</span>
                    <span className="score-badge">{v.score} / 10</span>
                  </div>
                  <p className="rationale">{v.rationale}</p>
                </div>
              ))}
            </div>

            {/* Explanation */}
            {result.explanation && (
              <div className="explanation-block">
                <p className="section-head" style={{ opacity: 1, animation: "none" }}>Venu Says</p>
                <p
                  className="explanation-text"
                  dangerouslySetInnerHTML={{ __html: renderExplanation(result.explanation) }}
                />
              </div>
            )}

            {/* Refine */}
            <div className="refine-block">
              <p className="refine-label">Refine Your Search</p>
              <div className="refine-row">
                <input
                  className="refine-input"
                  placeholder="e.g. actually prefer South End, make it more casual..."
                  value={refineText}
                  onChange={(e) => setRefineText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleRefine(); }}
                />
                <button
                  className="refine-btn"
                  onClick={handleRefine}
                  disabled={loading || !refineText.trim()}
                >
                  {loading ? "..." : "Refine"}
                </button>
              </div>
              <button className="reset-link" onClick={handleReset}>
                start over
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}