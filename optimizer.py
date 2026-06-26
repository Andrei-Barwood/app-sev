import numpy as np
from scipy.optimize import differential_evolution, least_squares
from core import calc_rho_a


def _data_driven_bounds(
    initial_params: np.ndarray,
    fixed_mask: np.ndarray,
    n_layers: int,
    L_med: np.ndarray,
    rho_med: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rho_data_min = max(float(np.min(rho_med)), 1e-3)
    rho_data_max = max(float(np.max(rho_med)), rho_data_min * 1.01)
    rho_min = 10 ** (np.log10(rho_data_min) - 1.0)
    rho_max = 10 ** (np.log10(rho_data_max) + 1.4)

    l_data_min = max(float(np.min(L_med)), 1e-3)
    l_data_max = max(float(np.max(L_med)), l_data_min * 1.01)
    h_min = 10 ** (np.log10(l_data_min) - 0.7)
    h_max = 10 ** (np.log10(l_data_max) + 0.6)

    lower = np.copy(initial_params)
    upper = np.copy(initial_params)
    for i, fixed in enumerate(fixed_mask):
        if fixed:
            continue
        if i < n_layers:
            lower[i] = rho_min
            upper[i] = rho_max
        else:
            lower[i] = h_min
            upper[i] = h_max
    return lower, upper


def _merge_free_params(free_values: np.ndarray, fixed_mask: np.ndarray, fixed_values: np.ndarray) -> np.ndarray:
    params = np.copy(fixed_values)
    params[~fixed_mask] = free_values
    return params


def _safe_log10(values: np.ndarray) -> np.ndarray:
    return np.log10(np.maximum(values, 1e-6))


def _objective_mse_log(
    free_values: np.ndarray,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    n_layers: int,
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
) -> float:
    params = _merge_free_params(free_values, fixed_mask, fixed_values)
    rho = params[:n_layers]
    h = params[n_layers:]
    rho_calc = calc_rho_a(L_med, rho, h)
    return float(np.mean((_safe_log10(rho_med) - _safe_log10(rho_calc)) ** 2))


def _residuals_log(
    free_values: np.ndarray,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    n_layers: int,
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
) -> np.ndarray:
    params = _merge_free_params(free_values, fixed_mask, fixed_values)
    rho = params[:n_layers]
    h = params[n_layers:]
    rho_calc = calc_rho_a(L_med, rho, h)
    return _safe_log10(rho_calc) - _safe_log10(rho_med)


def _linear_to_log_bounds(lower: np.ndarray, upper: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return _safe_log10(lower), _safe_log10(upper)


def _log_to_linear(values_log: np.ndarray) -> np.ndarray:
    return 10 ** values_log


def run_optimization(L_med, rho_med, initial_rho, initial_h, fixed_rho, fixed_h, use_global=False):
    """
    Ejecuta el proceso de optimización en dos pasos.
    Los parámetros libres se optimizan en escala log10 para estabilidad numérica.
    """
    n_layers = len(initial_rho)

    initial_params = np.concatenate([initial_rho, initial_h])
    fixed_mask = np.array(fixed_rho + fixed_h, dtype=bool)
    fixed_values = np.copy(initial_params)

    free_params_initial = initial_params[~fixed_mask]
    n_free = len(free_params_initial)

    if n_free == 0:
        rho_calc = calc_rho_a(L_med, initial_rho, initial_h)
        rmse = np.sqrt(np.mean((rho_med - rho_calc) ** 2))
        ss_res = np.sum((_safe_log10(rho_med) - _safe_log10(rho_calc)) ** 2)
        ss_tot = np.sum((_safe_log10(rho_med) - np.mean(_safe_log10(rho_med))) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        return initial_rho, initial_h, rmse, r2

    lower_all, upper_all = _data_driven_bounds(
        initial_params, fixed_mask, n_layers, np.asarray(L_med), np.asarray(rho_med)
    )
    free_lower = lower_all[~fixed_mask]
    free_upper = upper_all[~fixed_mask]
    free_lower = np.minimum(free_lower, free_params_initial)
    free_upper = np.maximum(free_upper, free_params_initial)

    free_lower_log, free_upper_log = _linear_to_log_bounds(free_lower, free_upper)
    x0_log = np.clip(_safe_log10(free_params_initial), free_lower_log, free_upper_log)

    if use_global:
        bounds_log = list(zip(free_lower_log, free_upper_log))
        result_global = differential_evolution(
            lambda x: _objective_mse_log(
                _log_to_linear(x), L_med, rho_med, n_layers, fixed_mask, fixed_values
            ),
            bounds=bounds_log,
            strategy="best1bin",
            maxiter=800,
            popsize=18,
            tol=1e-3,
            mutation=(0.5, 1.0),
            recombination=0.7,
            disp=False,
            seed=42,
            polish=False,
        )
        x0_log = np.clip(result_global.x, free_lower_log, free_upper_log)

    result_local = least_squares(
        lambda x: _residuals_log(
            _log_to_linear(x), L_med, rho_med, n_layers, fixed_mask, fixed_values
        ),
        x0=x0_log,
        bounds=(free_lower_log, free_upper_log),
        method="trf",
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=4000,
    )

    best_free_final = _log_to_linear(result_local.x)

    final_params = _merge_free_params(best_free_final, fixed_mask, fixed_values)
    best_rho = final_params[:n_layers]
    best_h = final_params[n_layers:]

    rho_calc = calc_rho_a(L_med, best_rho, best_h)
    rmse = np.sqrt(np.mean((rho_med - rho_calc) ** 2))
    ss_res = np.sum((_safe_log10(rho_med) - _safe_log10(rho_calc)) ** 2)
    ss_tot = np.sum((_safe_log10(rho_med) - np.mean(_safe_log10(rho_med))) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return list(best_rho), list(best_h), rmse, r2