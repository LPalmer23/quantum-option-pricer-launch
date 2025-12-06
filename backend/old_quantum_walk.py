"""
Quantum random walk + call option pricing
Qiskit 1.x compatible

Features (improved):
  - Log-space price grid from ±kσ bounds (Black–Scholes lognormal distribution)
  - Drift encoded via risk-neutral CRR-style coin
  - Quantum walk over the price index
  - Calibration step to match risk-neutral mean E[S_T] = S0 * exp(rT)
  - Expected value calculator for S_T and payoff
  - Direct comparison with analytic Black–Scholes price
"""

import math
import numpy as np
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram


# -----------------------------
# 0. Black–Scholes closed form
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


# -----------------------------
# 1. Model / discretization parameters
# -----------------------------

# Option / market parameters
S0    = 100.0   # initial stock price
K     = 100.0   # strike
r     = 0.02    # risk-free rate
sigma = 0.2     # volatility
T     = 5.0     # maturity (years)

# Quantum discretization
n_p     = 9       # number of price qubits -> 2^n_p bins
N_steps = 50      # number of time steps in the walk
num_bins = 2 ** n_p

# --- Time step and CRR-style up/down factors ---
dt = T / N_steps                         # time step
u  = math.exp(sigma * math.sqrt(dt))     # up factor
d  = math.exp(-sigma * math.sqrt(dt))    # down factor

# Risk-neutral up probability (Cox–Ross–Rubinstein)
p_up   = (math.exp(r * dt) - d) / (u - d)
eps    = 1e-6
p_up   = min(max(p_up, eps), 1.0 - eps)  # clamp to (0,1)
p_down = 1.0 - p_up

theta  = 2 * math.asin(math.sqrt(p_up))   # rotation angle for the coin

print("\n=== Drift / volatility parameters (CRR) ===")
print(f"dt      = {dt:.4f}")
print(f"u       = {u:.4f}, d = {d:.4f}")
print(f"p_up    = {p_up:.4f}, p_down = {p_down:.4f}")
print(f"theta   = {theta:.4f} rad")


# -----------------------------
# 2. Log-space price grid from ±kσ bounds
# -----------------------------

def compute_bounds_ksigma(S0, r, sigma, T, k_std=3.0):
    """
    Compute S_min, S_max as ±k_std standard deviations in LOG space
    for geometric Brownian motion (Black–Scholes model).

    log S_T ~ N(mu, sigma_T^2)
      mu      = ln(S0) + (r - 0.5*sigma^2)*T
      sigma_T = sigma*sqrt(T)

    Then:
      S_min = exp(mu - k_std*sigma_T)
      S_max = exp(mu + k_std*sigma_T)
    """
    mu = math.log(S0) + (r - 0.5 * sigma**2) * T
    sigma_T = sigma * math.sqrt(T)
    S_min = math.exp(mu - k_std * sigma_T)
    S_max = math.exp(mu + k_std * sigma_T)
    return S_min, S_max


# Use ±3σ bounds in log-space
S_min, S_max = compute_bounds_ksigma(S0, r, sigma, T, k_std=3.0)

# Logarithmic price grid between S_min and S_max
ratio = (S_max / S_min) ** (1.0 / (num_bins - 1))
prices = [S_min * (ratio ** k) for k in range(num_bins)]

# Find bin index closest to S0 as starting point
k0 = min(range(num_bins), key=lambda k: abs(prices[k] - S0))

print("\n=== Price grid from 3σ log-space bounds (logarithmic spacing) ===")
print(f"S_min ≈ {S_min:.4f}, S_max ≈ {S_max:.4f}, ratio ≈ {ratio:.4f}")
print(f"Using initial bin k0 = {k0}, S[k0] ≈ {prices[k0]:.4f}")


# -----------------------------
# 3. Quantum walk primitives
# -----------------------------

def prepare_price_basis_state(qc, price_reg, k_index):
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


def walk_step(qc, price_reg, coin_qubit, theta):
    """
    One quantum random-walk step:

      1. R_y(theta) on the coin: encodes p_up / p_down.
      2. If coin=1: increment price index.
      3. If coin=0: decrement price index.
    """
    # 1. Quantum coin
    qc.ry(theta, coin_qubit)

    # 2. If coin == |1>, increment price index
    controlled_increment(qc, price_reg, coin_qubit)

    # 3. If coin == |0>, decrement price index
    qc.x(coin_qubit)
    controlled_decrement(qc, price_reg, coin_qubit)
    qc.x(coin_qubit)


# -----------------------------
# 4. Build and run the circuit
# -----------------------------

price   = QuantumRegister(n_p, 'price')
coin    = QuantumRegister(1,   'coin')
c_price = ClassicalRegister(n_p, 'c_price')

qc = QuantumCircuit(price, coin, c_price)

# Initialize price register to |k0> (S ≈ S0)
prepare_price_basis_state(qc, price, k0)

# Apply N_steps of the random walk
for _ in range(N_steps):
    walk_step(qc, price, coin[0], theta)

# Measure price register
qc.measure(price, c_price)

print("\n=== Circuit ===")
print(qc)

backend = Aer.get_backend("qasm_simulator")
shots   = 4096

qc_t   = transpile(qc, backend)
result = backend.run(qc_t, shots=shots).result()
counts = result.get_counts()

print("\nRaw measurement counts (bitstrings):")
print(counts)


# -----------------------------
# 5. Map bitstrings → prices (probabilities)
# -----------------------------

probabilities = {}
for bitstring, c in counts.items():
    k = int(bitstring, 2)
    probabilities[k] = c / shots

print("\nEstimated terminal distribution over bins (non-zero probs):")
for k in sorted(probabilities.keys()):
    print(f"  k={k}, S_k={prices[k]:.2f}, p_k≈{probabilities[k]:.4f}")


# -----------------------------
# 6. Calibration + option pricing
# -----------------------------

discount_factor = math.exp(-r * T)

# First: raw E[S_T] from the quantum walk
E_ST_raw = 0.0
for k, p_k in probabilities.items():
    S_k = prices[k]
    E_ST_raw += p_k * S_k

# Target mean under risk-neutral measure
target_mean_ST = S0 * math.exp(r * T)

alpha = target_mean_ST / E_ST_raw if E_ST_raw != 0 else 1.0

print("\n=== Calibration ===")
print(f"E[S_T]_raw (quantum)   ≈ {E_ST_raw:.4f}")
print(f"E[S_T]_BS (target)     ≈ {target_mean_ST:.4f}")
print(f"Scaling factor alpha   ≈ {alpha:.4f}")

# Now recompute expectations using scaled prices
E_ST     = 0.0
E_payoff = 0.0

for k, p_k in probabilities.items():
    S_eff = alpha * prices[k]        # calibrated price
    payoff = max(S_eff - K, 0.0)

    E_ST     += p_k * S_eff
    E_payoff += p_k * payoff

call_price_est = discount_factor * E_payoff

print("\n=== Expected values from calibrated quantum walk ===")
print(f"E[S_T] (calibrated)    ≈ {E_ST:.4f}")
print(f"E[max(S_T - K, 0)]     ≈ {E_payoff:.4f}")
print(f"Discount factor e^(-rT) = {discount_factor:.6f}")
print(f"Call price estimate     ≈ {call_price_est:.4f}")


# ----------------------------------------
# 7. Compare with analytic Black–Scholes call
# ----------------------------------------
bs_call = black_scholes_call_price(S0, K, r, sigma, T)

abs_err = abs(call_price_est - bs_call)
rel_err = abs_err / bs_call if bs_call != 0 else float("inf")

print("\n=== Comparison with Black–Scholes formula ===")
print(f"Black–Scholes call price : {bs_call:.4f}")
print(f"Quantum walk call price  : {call_price_est:.4f}")
print(f"Absolute error           : {abs_err:.4f}")
print(f"Relative error           : {100*rel_err:.2f}%")


# -----------------------------
# 8. Plot histogram over price bins
# -----------------------------

labelled_counts = {
    f"k={k}\nS={prices[k]:.1f}": counts.get(format(k, f'0{n_p}b'), 0)
    for k in range(num_bins)
}

plt.figure()
plot_histogram(labelled_counts)
plt.title(f"Terminal price distribution from quantum walk (steps={N_steps})")
plt.tight_layout()
plt.show()
