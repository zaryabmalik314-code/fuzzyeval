import { useState, useEffect } from "react";
import "./App.css";

const API = "/api";

const CRITERIA = [
  { name: "Relevance", desc: "How well it addresses the prompt" },
  { name: "Accuracy", desc: "Factual correctness" },
  { name: "Completeness", desc: "How thoroughly it covers the topic" },
  { name: "Clarity", desc: "How clear and well-structured it is" },
];

const LABELS = { 1: "Very Poor", 2: "Poor", 3: "Fair", 4: "Good", 5: "Very Good" };

const GROQ_MODELS = [
  { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B" },
  { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B" },
  { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B" },
  { id: "gemma2-9b-it", name: "Gemma 2 9B" },
];

const GEMINI_MODELS = [
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash" },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash" },
];

function App() {
  const [groqKey, setGroqKey] = useState(() => localStorage.getItem("groq_key") || "");
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem("gemini_key") || "");
  const [groqModel, setGroqModel] = useState("llama-3.3-70b-versatile");
  const [geminiModel, setGeminiModel] = useState("gemini-2.0-flash");

  const [step, setStep] = useState("input");
  const [prompt, setPrompt] = useState("");
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ratings, setRatings] = useState({});
  const [weights, setWeights] = useState([5, 4, 3, 3]);
  const [results, setResults] = useState(null);

  useEffect(() => { localStorage.setItem("groq_key", groqKey); }, [groqKey]);
  useEffect(() => { localStorage.setItem("gemini_key", geminiKey); }, [geminiKey]);

  const handleQuery = async () => {
    if (!prompt.trim()) return;
    if (!groqKey || !geminiKey) { setError("Enter both API keys"); return; }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          groq_api_key: groqKey,
          gemini_api_key: geminiKey,
          groq_model: groqModel,
          gemini_model: geminiModel,
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      if (data.responses.some((r) => r.error)) {
        setError(data.responses.filter((r) => r.error).map((r) => `${r.model_name}: ${r.error}`).join("\n"));
      }
      const valid = data.responses.filter((r) => !r.error);
      setResponses(valid);
      const init = {};
      valid.forEach((r) => { init[r.model_name] = [3, 3, 3, 3]; });
      setRatings(init);
      setStep("responses");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleEvaluate = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ratings,
          criteria_weights: weights,
          criteria_names: CRITERIA.map((c) => c.name),
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setResults(await res.json());
      setStep("results");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const updateRating = (model, idx, val) => {
    setRatings((p) => ({ ...p, [model]: p[model].map((v, i) => i === idx ? val : v) }));
  };
  const updateWeight = (idx, val) => {
    setWeights((p) => p.map((v, i) => i === idx ? val : v));
  };
  const reset = () => {
    setStep("input"); setPrompt(""); setResponses([]); setRatings({}); setResults(null); setError(null);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🔍 FuzzyEval</h1>
        <p className="subtitle">Fuzzy TOPSIS Chatbot Response Evaluator</p>
        <div className="step-indicator">
          {["input", "responses", "evaluate", "results"].map((s, i) => (
            <span key={s} className={`step-dot ${step === s ? "active" : ""} ${["input","responses","evaluate","results"].indexOf(step) > i ? "done" : ""}`}>
              {i + 1}
            </span>
          ))}
        </div>
      </header>

      {error && <div className="error-banner" onClick={() => setError(null)}>⚠️ {error} <span className="close">×</span></div>}

      {/* ── STEP 1: Input ──────────────────────────── */}
      {step === "input" && (
        <div className="section fade-in">
          <div className="keys-row">
            <div className="key-input">
              <label>🟢 Groq API Key</label>
              <input type="password" value={groqKey} onChange={(e) => setGroqKey(e.target.value)} placeholder="gsk_..." />
              <select value={groqModel} onChange={(e) => setGroqModel(e.target.value)}>
                {GROQ_MODELS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div>
            <div className="key-input">
              <label>🔵 Gemini API Key</label>
              <input type="password" value={geminiKey} onChange={(e) => setGeminiKey(e.target.value)} placeholder="AI..." />
              <select value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)}>
                {GEMINI_MODELS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div>
          </div>

          <div className="prompt-section">
            <label>Your Prompt</label>
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask something... e.g. 'Explain quantum computing in simple terms'" rows={4} />
            <button className="btn primary" onClick={handleQuery} disabled={loading || !prompt.trim()}>
              {loading ? "⏳ Querying..." : "🚀 Send to Groq & Gemini"}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 2: Responses ──────────────────────── */}
      {step === "responses" && (
        <div className="section fade-in">
          <h2>📝 Responses</h2>
          <p className="prompt-echo">Prompt: <em>"{prompt}"</em></p>
          <div className="responses-grid">
            {responses.map((r) => (
              <div key={r.model_name} className="response-card">
                <div className="response-header">
                  <span className={`badge ${r.provider}`}>{r.provider}</span>
                  <strong>{r.model_name}</strong>
                </div>
                <div className="response-body">{r.response_text}</div>
              </div>
            ))}
          </div>
          <div className="action-row">
            <button className="btn secondary" onClick={reset}>← Start Over</button>
            <button className="btn primary" onClick={() => setStep("evaluate")}>✅ Rate These Responses →</button>
          </div>
        </div>
      )}

      {/* ── STEP 3: Evaluate ───────────────────────── */}
      {step === "evaluate" && (
        <div className="section fade-in">
          <h2>⚖️ Rate & Set Weights</h2>

          <div className="weights-panel">
            <h3>Criteria Importance</h3>
            <div className="weights-grid">
              {CRITERIA.map((c, idx) => (
                <div key={c.name} className="weight-item">
                  <label>{c.name}</label>
                  <div className="slider-row">
                    <input type="range" min={1} max={5} value={weights[idx]}
                      onChange={(e) => updateWeight(idx, parseInt(e.target.value))} />
                    <span className="weight-value">{weights[idx]}/5</span>
                  </div>
                  <span className="weight-desc">{c.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rating-matrix">
            {responses.map((r) => (
              <div key={r.model_name} className="rating-card">
                <h3><span className={`badge ${r.provider}`}>{r.provider}</span> {r.model_name}</h3>
                <div className="response-preview">{r.response_text.slice(0, 150)}...</div>
                {CRITERIA.map((c, idx) => (
                  <div key={c.name} className="rating-row">
                    <label>{c.name}</label>
                    <div className="rating-buttons">
                      {[1, 2, 3, 4, 5].map((v) => (
                        <button key={v}
                          className={`rate-btn ${ratings[r.model_name]?.[idx] === v ? "active" : ""}`}
                          onClick={() => updateRating(r.model_name, idx, v)} title={LABELS[v]}>
                          {v}
                        </button>
                      ))}
                    </div>
                    <span className="rating-label">{LABELS[ratings[r.model_name]?.[idx] || 3]}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="action-row">
            <button className="btn secondary" onClick={() => setStep("responses")}>← Back</button>
            <button className="btn primary" onClick={handleEvaluate} disabled={loading}>
              {loading ? "⏳ Running Fuzzy TOPSIS..." : "🧮 Evaluate"}
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 4: Results ────────────────────────── */}
      {step === "results" && results && (
        <div className="section fade-in">
          <h2>🏆 Results</h2>

          <div className="winner-banner">
            <div className="winner-icon">👑</div>
            <div>
              <h3>{results.explanation.winner}</h3>
              <p>{results.explanation.summary}</p>
            </div>
          </div>

          <div className="ranking-table">
            <table>
              <thead>
                <tr><th>Rank</th><th>Model</th><th>CC Score</th><th>d⁺</th><th>d⁻</th><th>Centroid</th></tr>
              </thead>
              <tbody>
                {results.explanation.ranking_detail.map((r) => (
                  <tr key={r.model} className={r.rank === 1 ? "winner-row" : ""}>
                    <td className="rank-cell">#{r.rank}</td>
                    <td><strong>{r.model}</strong></td>
                    <td className="score-cell">{r.cc}</td>
                    <td>{results.scores[r.model].d_plus}</td>
                    <td>{results.scores[r.model].d_minus}</td>
                    <td>{results.scores[r.model].centroid}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {results.explanation.separability && (
            <div className={`sep-badge ${results.explanation.separability.confidence.includes("close") ? "close" : results.explanation.separability.confidence.includes("moderate") ? "moderate" : "clear"}`}>
              Gap: {results.explanation.separability.cc_difference} — {results.explanation.separability.confidence}
            </div>
          )}

          <div className="breakdown">
            <h3>📊 Per-Criterion Breakdown</h3>
            <div className="breakdown-grid">
              {results.explanation.criterion_breakdown.map((cb) => (
                <div key={cb.criterion} className="breakdown-card">
                  <h4>{cb.criterion} <span className="weight-tag">w={cb.weight}</span></h4>
                  {Object.entries(cb.scores).map(([model, s]) => (
                    <div key={model} className="breakdown-row">
                      <span className={model === cb.best ? "best-marker" : ""}>{model}</span>
                      <div className="rating-bar"><div className="bar-fill" style={{ width: `${(s.rating / 5) * 100}%` }} /></div>
                      <span>{s.rating}/5 ({s.label})</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <div className="drivers">
            <h3>🎯 What Drove the Result</h3>
            <ul>{results.explanation.top_drivers.map((d, i) => <li key={i}>{d}</li>)}</ul>
          </div>

          <details className="fuzzy-details">
            <summary>🔬 Fuzzy Math Details</summary>
            <div className="details-content">
              <h4>Normalized Weights</h4>
              <pre>{JSON.stringify(results.weights, null, 2)}</pre>
              {results.ranking.map((model) => (
                <div key={model}>
                  <h4>{model}</h4>
                  <p>Aggregate TFN: ({results.scores[model].aggregate_tfn.l}, {results.scores[model].aggregate_tfn.m}, {results.scores[model].aggregate_tfn.u})</p>
                  <h5>Weighted TFNs:</h5>
                  <pre>{JSON.stringify(results.scores[model].weighted_tfns, null, 2)}</pre>
                </div>
              ))}
            </div>
          </details>

          <div className="action-row">
            <button className="btn secondary" onClick={() => setStep("evaluate")}>← Re-rate</button>
            <button className="btn primary" onClick={reset}>🔄 New Evaluation</button>
          </div>
        </div>
      )}

      <footer className="footer">
        FuzzyEval — Fuzzy TOPSIS Chatbot Response Assessment<br/>
        <small>Chen (2000) · Triangular Fuzzy Numbers · δ=0.25</small>
      </footer>
    </div>
  );
}

export default App;
