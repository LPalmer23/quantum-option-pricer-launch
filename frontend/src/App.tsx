import AgentChat from "./AgentChat";
import React, { useState, useEffect } from "react";
import "./App.css";
import TerminalDistributionPlot from "./TerminalDistributionPlot";



type PricingResponse = {
  inputs: {
    S0: number;
    K: number;
    r: number;
    sigma: number;
    T: number;
    N_steps: number;
    shots: number;
    calibrate: boolean;
  };
  model_params: {
    dt: number;
    u: number;
    d: number;
    p_up: number;
    p_down: number;
    theta: number;
    n_p: number;
    num_bins: number;
  };
  outputs: {
    bs_call: number;
    q_call_raw: number;
    q_call_calibrated: number;
    E_ST_raw?: number;
    E_ST_calibrated?: number;
    discount_factor: number;
  };
  errors: {
    raw: { abs: number; rel: number };
    calibrated: { abs: number; rel: number };
  };
  histogram: { k: number; S: number; prob: number }[];
};

function App() {

  const [showCalibInfo, setShowCalibInfo] = useState(false);

  // Form state
  const [S0, setS0] = useState("100");
  const [K, setK] = useState("100");
  const [r, setR] = useState("0.02");
  const [sigma, setSigma] = useState("0.2");
  const [T, setT] = useState("5");
  const [NSteps, setNSteps] = useState("50");
  const [shots, setShots] = useState("4096");
  const [calibrate, setCalibrate] = useState(true);
  

  // Result + UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PricingResponse | null>(null);
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowIntro(false), 1800); // 1.8s
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    function handleClick() {
      setShowCalibInfo(false);  // closes tooltip
    }
  
    if (showCalibInfo) {
      window.addEventListener("click", handleClick);
    }
  
    return () => {
      window.removeEventListener("click", handleClick);
    };
  }, [showCalibInfo]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        S0: Number(S0),
        K: Number(K),
        r: Number(r),
        sigma: Number(sigma),
        T: Number(T),
        N_steps: Number(NSteps),
        calibrate,
        shots: Number(shots),
      };

      const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

      const res = await fetch(`${API_URL}/price`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server error ${res.status}: ${text}`);
      }

      const data: PricingResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message ?? "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  // One single return
  return (
    <>
      {/* Lens intro overlay */}
      {showIntro && (
        <div className="lens-overlay">
          <div className="lens-circle" />
          <p className="lens-text">Initializing quantum engine…</p>
        </div>
      )}

      {/* Main UI – only when intro finished */}
      {!showIntro && (
        <div className="app">
          <header className="header">
            <h1>ZyQ Labs – Quantum Option Pricer</h1>
            <p>
              Compare a classical Black–Scholes price with our quantum random
              walk engine. Change the inputs and see how the prices and errors
              move.
            </p>
          </header>

          <main className="layout">
            {/* Left: input form */}
            <section className="card">
              <h2>Inputs</h2>
              <form onSubmit={handleSubmit} className="form-grid">
                <label>
                  S₀ (initial price)
                  <input
                    type="number"
                    step="0.01"
                    value={S0}
                    onChange={(e) => setS0(e.target.value)}
                  />
                </label>

                <label>
                  K (strike)
                  <input
                    type="number"
                    step="0.01"
                    value={K}
                    onChange={(e) => setK(e.target.value)}
                  />
                </label>

                <label>
                  r (risk-free rate)
                  <input
                    type="number"
                    step="0.001"
                    value={r}
                    onChange={(e) => setR(e.target.value)}
                  />
                </label>

                <label>
                  σ (volatility)
                  <input
                    type="number"
                    step="0.01"
                    value={sigma}
                    onChange={(e) => setSigma(e.target.value)}
                  />
                </label>

                <label>
                  T (years to maturity)
                  <input
                    type="number"
                    step="0.25"
                    value={T}
                    onChange={(e) => setT(e.target.value)}
                  />
                </label>

                <label>
                  N_steps (time steps)
                  <input
                    type="number"
                    step="1"
                    value={NSteps}
                    onChange={(e) => setNSteps(e.target.value)}
                  />
                </label>

                <label>
                  Shots (simulator runs)
                  <input
                    type="number"
                    step="1"
                    value={shots}
                    onChange={(e) => setShots(e.target.value)}
                  />
                </label>

                <label className="checkbox-row calibrate-row">
                <input
                  type="checkbox"
                  checked={calibrate}
                  onChange={(e) => setCalibrate(e.target.checked)}
                />

                <span className="calibrate-text">
                  Calibrate quantum walk to match E[Sₜ]

                  {/* Info icon */}
                  <span
                    className="calib-info-icon"
                    onClick={(e) => {
                      e.preventDefault();      // don't toggle checkbox
                      e.stopPropagation();     // don't bubble up to the label
                      setShowCalibInfo((v) => !v);
                    }}
                    onMouseDown={(e) => e.preventDefault()} // prevent focus/press from toggling
                  >
                    ⓘ
                  </span>


                  {/* Small floating bubble tooltip */}
                  {showCalibInfo && (
                    <div className="calib-tooltip">
                      <p>
                        Aligns the quantum walk’s expected value E[Sₜ] with the
                        classical Black–Scholes expectation.  
                        Makes comparisons more fair.  
                      </p>
                    </div>
                  )}
                </span>
              </label>



                <button type="submit" disabled={loading}>
                  {loading ? "Running quantum walk…" : "Run Quantum Pricing"}
                </button>
              </form>

              {error && <p className="error">⚠️ {error}</p>}
            </section>

            {/* Right: results */}
            <section className="card">
              <h2>Results</h2>
              {!result && !loading && (
                <p className="muted">
                  Run the pricer to see Black–Scholes vs quantum results.
                </p>
              )}

              {result && (
                <>
                  <div className="results-grid">
                    <div className="stat">
                      <h3>Black–Scholes Call</h3>
                      <p className="big">
                        ${result.outputs.bs_call.toFixed(2)}
                      </p>
                      <p className="muted">
                        Classical closed-form solution
                      </p>
                    </div>

                    <div className="stat">
                      <h3>Quantum Call (calibrated)</h3>
                      <p className="big">
                        ${result.outputs.q_call_calibrated.toFixed(2)}
                      </p>
                      <p className="muted">
                        After matching E[S<sub>T</sub>] to Black–Scholes
                      </p>
                    </div>

                    <div className="stat">
                      <h3>Calibration Error</h3>
                      <p className="big">
                        {result.errors.calibrated.abs.toFixed(3)}
                      </p>
                      <p className="muted">
                        |C<sub>quantum</sub> − C<sub>BS</sub>| (absolute)
                      </p>
                    </div>

                    <div className="stat">
                      <h3>Relative Error</h3>
                      <p className="big">
                        {(result.errors.calibrated.rel * 100).toFixed(2)}%
                      </p>
                      <p className="muted">
                        Relative to Black–Scholes price
                      </p>
                    </div>
                  </div>

                  <h3>Sample of Terminal Price Distribution</h3>
                  <TerminalDistributionPlot histogram={result.histogram} />



                  <p className="muted">
                    These are a few of the price bins from the quantum walk:
                  </p>
                  <table className="histogram">
                    <thead>
                      <tr>
                        <th>k (bin)</th>
                        <th>
                          S<sub>k</sub>
                        </th>
                        <th>Probability</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.histogram.slice(0, 12).map((bin) => (
                        <tr key={bin.k}>
                          <td>{bin.k}</td>
                          <td>{bin.S.toFixed(2)}</td>
                          <td>{bin.prob.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>
          </main>

          {/* About / How it works card */}
          <section className="card about-card">
            <h2>About this project</h2>
            <p className="muted about-intro">
              This demo compares a classical Black–Scholes call option price
              with a quantum-inspired random walk built in Qiskit.
            </p>
            <ul className="about-list">
              <li>
                <strong>Left side:</strong> you choose the market parameters:
                S₀, strike K, risk-free rate r, volatility σ, maturity T,
                number of time steps, and simulator shots.
              </li>
              <li>
                <strong>Under the hood:</strong> the backend (FastAPI + Qiskit)
                builds an 8-qubit price register and a coin qubit, runs a
                quantum random walk, and maps measurement outcomes to a
                terminal price distribution.
              </li>
              <li>
                <strong>Right side:</strong> you see the classical
                Black–Scholes call, the calibrated quantum call price, and
                their absolute & relative errors.
              </li>
              <li>
                <strong>Histogram sample:</strong> shows a slice of the quantum
                terminal distribution – each row is one price bin a simulated
                path can land in.
              </li>
            </ul>
            <p className="about-footnote">
              Built by Lydia Palmer & Zack as a hackathon prototype exploring
              how quantum-style algorithms can be wrapped in real, interactive
              tools.
            </p>
          </section>
        </div>
      )}
      {!showIntro && <AgentChat />}
    </>
  );
}

export default App;
