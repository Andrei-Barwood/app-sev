import numpy as np
from scipy.optimize import differential_evolution, least_squares
from core import calc_rho_a

def objective_function_global(x, L_med, rho_med, n_layers, fixed_mask, fixed_values):
    """
    Función objetivo para differential_evolution.
    Combina parámetros fijos y libres para evaluar el RMSE.
    """
    params = np.copy(fixed_values)
    # Insertar los parámetros libres (x) en sus lugares correspondientes
    params[~fixed_mask] = x
    
    # Extraer rho y h
    rho = params[:n_layers]
    h = params[n_layers:]
    
    # Calcular resistividad teórica
    rho_calc = calc_rho_a(L_med, rho, h)
    
    # Calcular el error (podemos usar RMSE logarítmico para ajustar mejor varias décadas)
    # o error relativo porcentual. Usaremos MSE del logaritmo para evitar que valores grandes dominen
    # log10(rho) asegura buen ajuste en escala log-log
    error = np.mean((np.log10(rho_med) - np.log10(rho_calc))**2)
    return error

def objective_function_local(x, L_med, rho_med, n_layers, fixed_mask, fixed_values):
    """
    Función de residuos para least_squares.
    Retorna los residuos (diferencias) punto a punto.
    """
    params = np.copy(fixed_values)
    params[~fixed_mask] = x
    
    rho = params[:n_layers]
    h = params[n_layers:]
    
    rho_calc = calc_rho_a(L_med, rho, h)
    
    # Residuos en escala logarítmica
    residuals = np.log10(rho_calc) - np.log10(rho_med)
    return residuals

def run_optimization(L_med, rho_med, initial_rho, initial_h, fixed_rho, fixed_h):
    """
    Ejecuta el proceso de optimización en dos pasos.
    
    Parámetros:
    -----------
    L_med : array de distancias medidas
    rho_med : array de resistividades medidas
    initial_rho : lista de resistividades iniciales
    initial_h : lista de espesores iniciales
    fixed_rho : lista de booleanos indicando si rho[i] es fijo
    fixed_h : lista de booleanos indicando si h[i] es fijo
    
    Retorna:
    --------
    best_rho, best_h, rmse, r2 : Parámetros optimizados y métricas de error.
    """
    n_layers = len(initial_rho)
    
    # Consolidar parámetros
    initial_params = np.concatenate([initial_rho, initial_h])
    fixed_mask = np.array(fixed_rho + fixed_h, dtype=bool)
    fixed_values = np.copy(initial_params)
    
    # Parámetros libres
    free_params_initial = initial_params[~fixed_mask]
    n_free = len(free_params_initial)
    
    # Si no hay parámetros libres, devolvemos los iniciales
    if n_free == 0:
        rho_calc = calc_rho_a(L_med, initial_rho, initial_h)
        rmse = np.sqrt(np.mean((rho_med - rho_calc)**2))
        ss_res = np.sum((np.log10(rho_med) - np.log10(rho_calc))**2)
        ss_tot = np.sum((np.log10(rho_med) - np.mean(np.log10(rho_med)))**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        return initial_rho, initial_h, rmse, r2
    
    # Definir límites (bounds) basados en el valor inicial (ej: 0.1x a 10x)
    # Permite un amplio rango para differential_evolution
    bounds = []
    for val in free_params_initial:
        bounds.append((val * 0.01, val * 100.0))
        
    # === PASO 1: Optimización Global (Differential Evolution) ===
    # differential_evolution es estocástico y explora bien el espacio
    result_global = differential_evolution(
        objective_function_global,
        bounds=bounds,
        args=(L_med, rho_med, n_layers, fixed_mask, fixed_values),
        strategy='best1bin',
        maxiter=1000,
        popsize=15,
        tol=1e-3,
        mutation=(0.5, 1.0),
        recombination=0.7,
        seed=42, # Para reproducibilidad
        disp=False
    )
    
    best_free_global = result_global.x
    
    # === PASO 2: Refinamiento Local (Least Squares) ===
    # Usamos los resultados de la global como punto de partida local
    # Establecemos bounds strictos de > 0
    local_bounds = (np.zeros(n_free) + 1e-5, np.inf)
    
    result_local = least_squares(
        objective_function_local,
        x0=best_free_global,
        bounds=local_bounds,
        args=(L_med, rho_med, n_layers, fixed_mask, fixed_values),
        method='trf',
        loss='soft_l1', # Robusto frente a outliers
        f_scale=0.1
    )
    
    best_free_final = result_local.x
    
    # Reconstruir parámetros
    final_params = np.copy(fixed_values)
    final_params[~fixed_mask] = best_free_final
    
    best_rho = final_params[:n_layers]
    best_h = final_params[n_layers:]
    
    # Calcular métricas finales
    rho_calc = calc_rho_a(L_med, best_rho, best_h)
    
    # RMSE absoluto
    rmse = np.sqrt(np.mean((rho_med - rho_calc)**2))
    
    # R2 sobre los logaritmos (ya que las curvas abarcan órdenes de magnitud)
    ss_res = np.sum((np.log10(rho_med) - np.log10(rho_calc))**2)
    ss_tot = np.sum((np.log10(rho_med) - np.mean(np.log10(rho_med)))**2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return list(best_rho), list(best_h), rmse, r2
