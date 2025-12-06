
<img width="1449" height="305" alt="Screenshot 2025-12-06 at 8 29 54 PM" src="https://github.com/user-attachments/assets/772b8554-b2b4-4778-93e4-f4d715835e6f" />

## Overview

This project demonstrates a practical workflow for quantum-inspired option pricing.  
The frontend provides an interactive interface for experimenting with inputs, while the backend performs both:

- Closed-form Black–Scholes pricing  
- Quantum-style Monte Carlo simulation using a random-walk kernel  

The tool is deployed on Vercel with a Python API hosted on Render.

---

## Live Demo

Frontend (Vercel):  
https://quantum-option-pricer-launch-3fdf.vercel.app/

Backend (Render):  
https://quantum-option-pricer-launch.onrender.com

---

## Features

- Adjustable option parameters (spot price, strike, volatility, maturity, risk-free rate)
- Classical Black–Scholes analytical pricing
- Quantum-inspired random walk engine producing simulated payoffs
- Side-by-side comparison of classical vs. quantum price estimates
- Clean responsive UI with dark-themed gradient design
- FastAPI backend with CORS support for Vercel deployments

---

## Frontend

- **Framework:** React + TypeScript + Vite  
- **Styling:** Custom CSS  
- **API Integration:** Fetch requests to Render backend  

Key file:  
`frontend/src/App.tsx`

---

## Backend

- **Framework:** FastAPI (Python)  
- **Simulation:** Vectorized random walks using NumPy  
- **Classical Pricing:** Black–Scholes closed form  
- **Deployment:** Render  
- **CORS:** Configured for local development and Vercel

Key file:  
`backend/main.py`

---

## Local Development

### 1. Clone the repository
```bash
git clone https://github.com/LPalmerr23/quantum-option-pricer-launch.git
