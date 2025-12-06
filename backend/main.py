# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from quantum_engine import run_quantum_pricing  # your quantum code wrapper

# --- OpenAI client ---
from openai import OpenAI
import os

client = OpenAI()  # uses OPENAI_API_KEY from your environment


PROJECT_CONTEXT = """
You are the AI explainer for the 'ZyQ Labs – Quantum Option Pricer' project built by Lydia Palmer and Zack.

Context:
• This project was created for the Qiskit Fall Fest 2025, as part of the Quandela challenge hosted by Université Paris-Saclay.
• The hackathon ran from November 21 to November 28, 2025, and was a 1 week online event.
• The challenge asked participants to build or demonstrate a quantum random walk that can be used to discretize the Black Scholes PDE or to create a quantum flavored financial model.
• Our submission is an interactive quantum option pricing demo that compares a classical model with a quantum inspired one.

High-level:
• This is a quantum flavored option pricing demo.
• It compares a classical Black Scholes European call price with a quantum random walk simulation built in Qiskit.
• The user can adjust S0 (initial price), K (strike), r (risk free rate), sigma (volatility), T (years to maturity), N_steps (time steps), and shots (simulator runs).
• The Python backend is FastAPI and the frontend is React, TypeScript, and Vite.

Backend and algorithm:
• The file quantum_engine.py contains run_quantum_pricing, which builds a quantum random walk:
    • Uses 8 price qubits (256 bins) and 1 coin qubit.
    • Time steps N_steps ≈ 31.
    • Uses a CRR style up and down model with u and d based on volatility and a modified time scaling so that the quantum distribution spreads slightly faster than classical CRR.
    • Runs on the Qiskit Aer qasm simulator with a configurable number of shots.
    • Maps measurement counts to a price grid, computes E[S_T], E[max(S_T - K, 0)], and discounts to get a quantum call price estimate.
• It also computes a classical Black Scholes call price for the same parameters.
• The function returns:
    • inputs (S0, K, r, sigma, T, N_steps, shots, calibrate)
    • model_params (dt, u, d, p_up, p_down, theta, n_p, num_bins)
    • outputs (bs_call, q_call_raw, q_call_calibrated, discount_factor, etc.)
    • errors (absolute and relative error vs Black Scholes)
    • histogram of terminal prices (bin index, price, probability).

Frontend:
• The React app shows:
    • Left card with input form for S0, K, r, sigma, T, N_steps, shots, and a checkbox to calibrate the quantum walk.
    • Right card with Black Scholes call, quantum call (calibrated), calibration error, relative error, and a sample of the terminal distribution in a table.
• There is a galaxy style background and a lens intro animation when the app loads.
• A chat button allows users to ask questions through the AI agent.

Your role:
• Explain the project clearly to hackathon judges, students, or curious users.
• You can:
    • Explain what the site does and how to use it.
    • Explain basics of options, Black Scholes, random walks, and what is “quantum” here.
    • Describe how the backend and frontend communicate through FastAPI.
    • Answer “how was this built?” questions.
    • Provide intuition with optional deeper mathematical detail if requested.
• If users ask about code, provide high level explanations rather than long code dumps.
• If users ask about the hackathon story, explain that this was built quickly as a demo of quantum inspired finance with an interactive UI.

Always:
• Be friendly, concise, and encouraging.
• Assume the user has curiosity but may not know quantum computing.

Formatting rule:
Do not use em dashes in any responses. Replace them with commas, periods, or the word "and". Normal hyphens may still be used for math, variables, and code.
"""



app = FastAPI(
    title="ZyQ Labs – Quantum Option Pricing API",
    version="0.1.0"
)

# ---- CORS so React (localhost:5173) can call the API ----
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Request models ----

class PricingRequest(BaseModel):
    S0: float
    K: float
    r: float
    sigma: float
    T: float
    N_steps: int = 50
    shots: int = 4096
    calibrate: bool = True


class AgentRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"message": "ZyQ Labs Quantum Pricing API – use POST /price or /assistant"}


@app.post("/price")
def price_endpoint(req: PricingRequest):
    """
    Run the quantum pricing engine and return:
      - inputs, model_params, outputs, errors, histogram
    """
    result = run_quantum_pricing(
        S0=req.S0,
        K=req.K,
        r=req.r,
        sigma=req.sigma,
        T=req.T,
        N_steps=req.N_steps,
        shots=req.shots,
        calibrate=req.calibrate,
    )
    return result


@app.post("/assistant")
def assistant_endpoint(req: AgentRequest):
    """
    Simple AI agent that explains the project, quantum ideas, etc.
    Frontend will call this with { "message": "..." }.
    """
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": PROJECT_CONTEXT},
            {"role": "user", "content": req.message},
        ],
        temperature=0.6,
    )

    answer = completion.choices[0].message.content
    return {"answer": answer}
