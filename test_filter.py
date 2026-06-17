import numpy as np
from scipy.integrate import quad
import scipy.special as sp

def pekeris(lmbd, rho, h):
    T = np.full_like(lmbd, rho[-1], dtype=float)
    for i in range(len(rho)-2, -1, -1):
        th = np.tanh(lmbd * h[i])
        T = rho[i] * (T + rho[i]*th) / (rho[i] + T*th)
    return T

# Ghosh 9-point
c = [0.0225, -0.0499, 0.1064, 0.1854, 1.9720, -1.5716, 0.4018, -0.0814, 0.0148]
k_vals = np.arange(-3, 6)

def test_filter(L, rho, h):
    # Option 1: lambda = 10^(-k/3) / L
    lmbd1 = (10.0 ** (-k_vals / 3.0)) / L
    T1 = pekeris(lmbd1, rho, h)
    rho_a1 = np.sum(c * T1)
    
    # Option 2: lambda = 10^(k/3) / L
    lmbd2 = (10.0 ** (k_vals / 3.0)) / L
    T2 = pekeris(lmbd2, rho, h)
    rho_a2 = np.sum(c * T2)
    
    # True value using quad
    def integrand(lmbd):
        return lmbd * pekeris(np.array([lmbd]), rho, h)[0] * sp.j1(lmbd * L)
    
    true_val, _ = quad(integrand, 0, 50/L, limit=5000, epsabs=1e-3, epsrel=1e-3)
    true_val *= L**2
    
    print(f"L={L}: Option 1={rho_a1:.3f}, Option 2={rho_a2:.3f}, True={true_val:.3f}")

rho = [100.0, 10.0]
h = [5.0]

for L in [1.0, 5.0, 10.0, 50.0]:
    test_filter(L, rho, h)
