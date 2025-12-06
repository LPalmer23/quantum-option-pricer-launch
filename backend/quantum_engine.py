# backend/quantum_engine.py

"""
Quantum random walk + call option pricing (CRR-consistent)
Qiskit 1.x compatible

This module exposes a single function:

    run_quantum_pricing(S0, K, r, sigma, T, N_steps, calibrate=True)

which returns:
    - Black–Scholes call price
    - quantum call price (raw)
    - quantum call price (after mean calibration, if enabled)
    - errors
    - histogram data for plotting
"""

import math
import numpy as np

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import Aer


# -----------------------------
# Black–Scholes helpers
# -----------------------------

def norm_cdf(x: float) -> float:
    """Standard normal CDF using erf (no extra libraries needed)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_call_price(S0, K, r, sigma, T):
    """Closed-form Black–Scholes price for a European call option."""
    if T <= 0 or sigma <= 0:
        # If there is no time or no volatility, price is just intrinsic value
        return max(S0 - K, 0.0)

    d1 = (math.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    return S0 * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)



# Quantum walk building blocks

def prepare_price_basis_state(qc, price_reg, k_index: int):
    """
    Prepare |k_index> on price_reg.
    LSB is price_reg[0] (Qiskit convention).
    """
    binary = format(k_index, f"0{len(price_reg)}b")
    for i, bit in enumerate(reversed(binary)):  # reg[0] is LSB
        if bit == '1':
            qc.x(price_reg[i])


def controlled_increment(qc, reg, ctrl):
    """
    Controlled increment by +1 modulo 2^n on 'reg', with control qubit 'ctrl'.
    Simple ripple-carry style using multi-controlled X (mcx).
    """
    n = len(reg)

    # Flip LSB when ctrl=1
    qc.cx(ctrl, reg[0])

    # Propagate carries
    for i in range(1, n):
        controls = [ctrl] + [reg[j] for j in range(i)]
        qc.mcx(controls, reg[i])


def controlled_decrement(qc, reg, ctrl):
    """
    Controlled decrement by -1 modulo 2^n on 'reg', with control qubit 'ctrl'.

    Implement x -> x-1 mod 2^n by:
      x -> ~x
      controlled_increment
      x -> ~x
    """
    for q in reg:
        qc.x(q)
    controlled_increment(qc, reg, ctrl)
    for q in reg:
        qc.x(q)


def walk_step(qc, price_reg, coin_qubit, theta: float):
    """
    One quantum random-walk step:

      1. R_y(theta) on the coin: encodes p_up / p_down.
      2. If coin=1: increment price index.
      3. If coin=0: decrement price index.
    """
    qc.ry(theta, coin_qubit)                    # quantum coin
    controlled_increment(qc, price_reg, coin_qubit)

    qc.x(coin_qubit)                           # flip to control "down" branch
    controlled_decrement(qc, price_reg, coin_qubit)
    qc.x(coin_qubit)


# Main engine
def run_quantum_pricing(
    S0: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    N_steps: int = 50,
    calibrate: bool = True,
    shots: int = 4096,
):
    """
    Build and run a CRR-consistent quantum random walk for option pricing.

    Returns a dict with:
      - bs_call
      - q_call_raw
      - q_call_calibrated
      - errors
      - histogram (labels + probs)
      - model_params (n_p, num_bins, dt, u, d, p_up)
    """


        # --- 1. Modified step params for faster quantum spreading ---
    dt = T / N_steps

    # Instead of u = exp(sigma * sqrt(dt)),
    # use a "global" T scaling spread over N_steps:
    # u = exp( sigma * sqrt(T) / N_steps )
    step_vol = sigma * math.sqrt(T) / N_steps
    u = math.exp(step_vol)
    d = 1.0 / u


    # risk-neutral probabilities
    p_up = (math.exp(r * dt) - d) / (u - d)
    eps = 1e-6
    p_up = min(max(p_up, eps), 1.0 - eps)
    p_down = 1.0 - p_up

    theta = 2 * math.asin(math.sqrt(p_up))

    # --- 2. Grid size so we never hit edges ---
    min_bins = 4 * N_steps + 1
    n_p = math.ceil(math.log2(min_bins))
    num_bins = 2 ** n_p

    center = num_bins // 2
    k0 = center

    prices = []
    for k in range(num_bins):
        delta = k - center
        S_k = S0 * (u ** delta)
        prices.append(S_k)

    # --- 3. Build circuit ---
    price = QuantumRegister(n_p, "price")
    coin = QuantumRegister(1, "coin")
    c_price = ClassicalRegister(n_p, "c_price")

    qc = QuantumCircuit(price, coin, c_price)

    prepare_price_basis_state(qc, price, k0)

    for _ in range(N_steps):
        walk_step(qc, price, coin[0], theta)

    qc.measure(price, c_price)

    # --- 4. Run on simulator ---
    backend = Aer.get_backend("qasm_simulator")
    qc_t = transpile(qc, backend)
    result = backend.run(qc_t, shots=shots).result()
    counts = result.get_counts()

    # --- 5. Map to probabilities + payoff ---
    probs = {}
    for bitstring, c in counts.items():
        k = int(bitstring, 2)
        probs[k] = c / shots

    discount_factor = math.exp(-r * T)

    E_ST_raw = 0.0
    E_payoff_raw = 0.0

    for k, p_k in probs.items():
        S_k = prices[k]
        payoff = max(S_k - K, 0.0)
        E_ST_raw += p_k * S_k
        E_payoff_raw += p_k * payoff

    q_call_raw = discount_factor * E_payoff_raw

    # --- 6. Calibration (match mean to BS) ---
    bs_call = black_scholes_call_price(S0, K, r, sigma, T)
    E_ST_BS = S0 * math.exp(r * T)  # theoretical mean under BS

    if calibrate and E_ST_raw > 0:
        alpha = E_ST_BS / E_ST_raw
    else:
        alpha = 1.0

    E_ST_cal = 0.0
    E_payoff_cal = 0.0

    for k, p_k in probs.items():
        S_k_cal = alpha * prices[k]
        payoff_cal = max(S_k_cal - K, 0.0)
        E_ST_cal += p_k * S_k_cal
        E_payoff_cal += p_k * payoff_cal

    q_call_cal = discount_factor * E_payoff_cal

    # errors w.r.t. Black–Scholes
    def err_stats(q_price):
        abs_err = abs(q_price - bs_call)
        rel_err = abs_err / bs_call if bs_call != 0 else float("inf")
        return abs_err, rel_err

    abs_err_raw, rel_err_raw = err_stats(q_call_raw)
    abs_err_cal, rel_err_cal = err_stats(q_call_cal)

    # Build a simple histogram-friendly object
    histogram = []
    for k in sorted(probs.keys()):
        histogram.append({
            "k": k,
            "S": prices[k],
            "prob": probs[k],
        })

    return {
        "inputs": {
            "S0": S0,
            "K": K,
            "r": r,
            "sigma": sigma,
            "T": T,
            "N_steps": N_steps,
            "shots": shots,
            "calibrate": calibrate,
        },
        "model_params": {
            "dt": dt,
            "u": u,
            "d": d,
            "p_up": p_up,
            "p_down": p_down,
            "theta": theta,
            "n_p": n_p,
            "num_bins": num_bins,
        },
        "outputs": {
            "bs_call": bs_call,
            "q_call_raw": q_call_raw,
            "q_call_calibrated": q_call_cal,
            "E_ST_raw": E_ST_raw,
            "E_ST_calibrated": E_ST_cal,
            "discount_factor": discount_factor,
        },
        "errors": {
            "raw": {
                "abs": abs_err_raw,
                "rel": rel_err_raw,
            },
            "calibrated": {
                "abs": abs_err_cal,
                "rel": rel_err_cal,
            },
        },
        "histogram": histogram,
    }


# Optional: quick local test if you run this file directly
if __name__ == "__main__":
    res = run_quantum_pricing(100.0, 100.0, 0.02, 0.2, 5.0, N_steps=50)
    print("Black–Scholes call:", res["outputs"]["bs_call"])
    print("Quantum (raw)      :", res["outputs"]["q_call_raw"])
    print("Quantum (cal)      :", res["outputs"]["q_call_calibrated"])
    print("Raw rel error      :", res["errors"]["raw"]["rel"])
    print("Cal rel error      :", res["errors"]["calibrated"]["rel"])
