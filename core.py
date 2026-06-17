import numpy as np
from filtros import GHOSH_9_COEFFS, GHOSH_9_K

def pekeris_recurrence(lambdas, rho, h):
    """
    Calcula la resistividad transversal T(lambda) usando la recurrencia de Pekeris.
    
    Parámetros:
    -----------
    lambdas : array-like
        Valores de lambda (frecuencia espacial) a evaluar.
    rho : array-like
        Resistividades de las capas [rho_1, rho_2, ..., rho_n].
    h : array-like
        Espesores de las capas [h_1, h_2, ..., h_{n-1}].
        
    Retorna:
    --------
    T : array-like
        Valores de la resistividad transversal evaluados en lambdas.
    """
    n_layers = len(rho)
    lambdas = np.asarray(lambdas)
    
    if n_layers == 1:
        return np.full_like(lambdas, rho[0], dtype=float)
    
    # Empezamos desde la capa más profunda, que tiene espesor infinito
    T = np.full_like(lambdas, rho[-1], dtype=float)
    
    # Iteramos desde la penúltima capa hacia la superficie (i = n-2, ..., 0)
    for i in range(n_layers - 2, -1, -1):
        # Para evitar desbordamiento en tanh para valores grandes de lambda*h
        # tanh(x) converge rápidamente a 1
        x = lambdas * h[i]
        tanh_term = np.tanh(x)
        
        numerator = T + rho[i] * tanh_term
        denominator = rho[i] + T * tanh_term
        T = rho[i] * (numerator / denominator)
        
    return T

def calc_rho_a_single(L, rho, h):
    """
    Calcula la resistividad aparente teórica para un único valor de L (AB/2)
    utilizando el filtro lineal digital de Ghosh (1971).
    """
    k_vals = np.array(GHOSH_9_K)
    
    # Los abscisas del filtro: lambda_k = 10^(-k/3) / L
    # Opción 1 usada en modelado estándar
    lambdas = (10.0 ** (-k_vals / 3.0)) / L
    
    # Evaluación de T(lambda)
    T = pekeris_recurrence(lambdas, rho, h)
    
    # Convolución
    coeffs = np.array(GHOSH_9_COEFFS)
    rho_a = np.sum(coeffs * T)
    
    return rho_a

def calc_rho_a(L_array, rho, h):
    """
    Calcula la resistividad aparente teórica para un vector de distancias L.
    
    Parámetros:
    -----------
    L_array : array-like
        Distancias de semielectrodos de corriente (AB/2).
    rho : array-like
        Resistividades de las capas [rho_1, ..., rho_n]
    h : array-like
        Espesores de las capas [h_1, ..., h_{n-1}]
        
    Retorna:
    --------
    rho_a_array : np.ndarray
        Resistividades aparentes calculadas.
    """
    rho = np.asarray(rho, dtype=float)
    h = np.asarray(h, dtype=float)
    L_array = np.asarray(L_array, dtype=float)
    
    rho_a_array = np.zeros_like(L_array)
    for i, L in enumerate(L_array):
        # Evitar división por cero
        if L <= 0:
            rho_a_array[i] = np.nan
        else:
            rho_a_array[i] = calc_rho_a_single(L, rho, h)
            
    return rho_a_array

if __name__ == "__main__":
    # Test básico de core
    rho_test = [100.0, 10.0, 100.0]
    h_test = [5.0, 15.0]
    L_test = np.logspace(0, 3, 20)
    print("Test L:", L_test)
    print("Test Rho_a:", calc_rho_a(L_test, rho_test, h_test))
