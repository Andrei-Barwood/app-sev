from __future__ import annotations

import numpy as np
from scipy.optimize import differential_evolution, least_squares
from core import calc_rho_a
from sev_metrics import ACCEPTANCE_ERROR_PCT, linear_error_pct


def _data_driven_bounds(
    initial_params: np.ndarray,
    fixed_mask: np.ndarray,
    n_layers: int,
    L_med: np.ndarray,
    rho_med: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rho_data_min = max(float(np.min(rho_med)), 1e-3)
    rho_data_max = max(float(np.max(rho_med)), rho_data_min * 1.01)
    contrast = rho_data_max / rho_data_min
    rho_min = 10 ** (np.log10(rho_data_min) - 1.2)
    rho_span = 1.6 if contrast > 80 else 1.4
    rho_max = 10 ** (np.log10(rho_data_max) + rho_span)

    l_data_min = max(float(np.min(L_med)), 1e-3)
    l_data_max = max(float(np.max(L_med)), l_data_min * 1.01)
    h_min = max(l_data_min * 0.002, 0.001)
    h_max = max(l_data_max * 4.0, h_min * 20.0)

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


def _strict_penalty(rho_med: np.ndarray, rho_calc: np.ndarray, threshold_pct: float) -> np.ndarray:
    err_lin = linear_error_pct(rho_med, rho_calc)
    return np.maximum(0.0, err_lin - threshold_pct) / max(threshold_pct, 1e-6)


def _objective_mse_log(
    free_values: np.ndarray,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    n_layers: int,
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
    *,
    strict_mode: bool = False,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
) -> float:
    params = _merge_free_params(free_values, fixed_mask, fixed_values)
    rho = params[:n_layers]
    h = params[n_layers:]
    rho_calc = calc_rho_a(L_med, rho, h)
    mse_log = float(np.mean((_safe_log10(rho_med) - _safe_log10(rho_calc)) ** 2))
    if not strict_mode:
        return mse_log
    penalty = _strict_penalty(rho_med, rho_calc, threshold_pct)
    return mse_log + 8.0 * float(np.mean(penalty**2)) + 2.0 * float(np.max(penalty) ** 2)


def _residuals_log(
    free_values: np.ndarray,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    n_layers: int,
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
    *,
    strict_mode: bool = False,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
) -> np.ndarray:
    params = _merge_free_params(free_values, fixed_mask, fixed_values)
    rho = params[:n_layers]
    h = params[n_layers:]
    rho_calc = calc_rho_a(L_med, rho, h)
    log_res = _safe_log10(rho_calc) - _safe_log10(rho_med)
    if not strict_mode:
        return log_res
    penalty = _strict_penalty(rho_med, rho_calc, threshold_pct)
    return np.concatenate([log_res, penalty * 4.0])


def _linear_to_log_bounds(lower: np.ndarray, upper: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return _safe_log10(lower), _safe_log10(upper)


def _log_to_linear(values_log: np.ndarray) -> np.ndarray:
    return 10 ** values_log


def _fit_metrics(L_med, rho_med, rho_model, h_model) -> tuple[float, float]:
    rho_calc = calc_rho_a(L_med, rho_model, h_model)
    rmse = float(np.sqrt(np.mean((rho_med - rho_calc) ** 2)))
    ss_res = float(np.sum((_safe_log10(rho_med) - _safe_log10(rho_calc)) ** 2))
    ss_tot = float(np.sum((_safe_log10(rho_med) - np.mean(_safe_log10(rho_med))) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return rmse, r2


def _strict_rank(
    L_med: np.ndarray,
    rho_med: np.ndarray,
    rho_model: list[float],
    h_model: list[float],
    threshold_pct: float,
) -> tuple[int, float, float, float]:
    rho_calc = calc_rho_a(L_med, rho_model, h_model)
    err = linear_error_pct(rho_med, rho_calc)
    over = int(np.sum(err > threshold_pct))
    return (
        over,
        float(np.max(err)),
        float(np.mean(err)),
        -_fit_metrics(L_med, rho_med, rho_model, h_model)[1],
    )


def _alternate_layer_configs(
    initial_rho: list[float],
    initial_h: list[float],
    fixed_rho: list[bool],
    fixed_h: list[bool],
    *,
    rho_med: np.ndarray | None = None,
) -> list[tuple[list[float], list[float], list[bool], list[bool]]]:
    configs: list[tuple[list[float], list[float], list[bool], list[bool]]] = [
        (list(initial_rho), list(initial_h), list(fixed_rho), list(fixed_h))
    ]
    n_layers = len(initial_rho)
    if n_layers == 3:
        mid_h = float(np.median(initial_h)) if initial_h else 1.0
        configs.append(
            (
                [initial_rho[0], initial_rho[-1]],
                [mid_h],
                [False, False],
                [False],
            )
        )
        if rho_med is not None:
            rho_arr = np.asarray(rho_med, dtype=float)
            contrast = float(np.max(rho_arr) / max(float(np.min(rho_arr)), 1e-3))
            if contrast > 80:
                r1 = float(np.max(rho_arr))
                r4 = float(np.min(rho_arr))
                r2 = max(0.01, float(np.sqrt(r1 * r4)))
                r3 = max(0.01, float(np.exp((np.log(r1) + 2 * np.log(r4)) / 3)))
                h1 = max(0.001, mid_h * 0.1)
                h2 = max(0.01, mid_h * 0.5)
                h3 = max(0.1, mid_h * 2.0)
                configs.append(
                    (
                        [r1, r2, r3, r4],
                        [h1, h2, h3],
                        [False, False, False, False],
                        [False, False, False],
                    )
                )
    elif n_layers == 2:
        mid_rho = max(0.1, float(np.sqrt(initial_rho[0] * initial_rho[-1])))
        h1 = float(initial_h[0]) if initial_h else 1.0
        configs.append(
            (
                [initial_rho[0], mid_rho, initial_rho[-1]],
                [max(0.001, h1 * 0.25), max(0.1, h1 * 2.0)],
                [False, False, False],
                [False, False],
            )
        )
    elif n_layers == 4:
        mid_h = float(np.median(initial_h)) if initial_h else 1.0
        configs.append(
            (
                [initial_rho[0], initial_rho[-1]],
                [mid_h],
                [False, False],
                [False],
            )
        )
        configs.append(
            (
                initial_rho[:3],
                initial_h[:2],
                [False, False, False],
                [False, False],
            )
        )
        if rho_med is not None:
            rho_arr = np.asarray(rho_med, dtype=float)
            configs.append(
                (
                    [float(np.max(rho_arr)), float(np.median(rho_arr)), float(np.min(rho_arr) * 2), float(np.min(rho_arr))],
                    [max(0.001, mid_h * 0.05), max(0.01, mid_h * 0.2), max(0.1, mid_h)],
                    [False, False, False, False],
                    [False, False, False],
                )
            )
    return configs


def _optimize_single_configuration(
    L_med,
    rho_med,
    initial_rho,
    initial_h,
    fixed_rho,
    fixed_h,
    use_global: bool = False,
    *,
    strict_polish: bool = False,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
):
    n_layers = len(initial_rho)
    initial_params = np.concatenate([initial_rho, initial_h])
    fixed_mask = np.array(fixed_rho + fixed_h, dtype=bool)
    fixed_values = np.copy(initial_params)

    free_params_initial = initial_params[~fixed_mask]
    if len(free_params_initial) == 0:
        rmse, r2 = _fit_metrics(L_med, rho_med, initial_rho, initial_h)
        return list(initial_rho), list(initial_h), rmse, r2

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
        seeds = (42, 7, 19) if n_layers <= 3 else (42,)
        best_global_x = None
        best_global_obj = float("inf")
        for seed in seeds:
            result_global = differential_evolution(
                lambda x: _objective_mse_log(
                    _log_to_linear(x),
                    L_med,
                    rho_med,
                    n_layers,
                    fixed_mask,
                    fixed_values,
                ),
                bounds=bounds_log,
                strategy="best1bin",
                maxiter=1200,
                popsize=22,
                tol=1e-4,
                mutation=(0.5, 1.0),
                recombination=0.7,
                disp=False,
                seed=seed,
                polish=False,
            )
            if result_global.fun < best_global_obj:
                best_global_obj = result_global.fun
                best_global_x = result_global.x
        if best_global_x is not None:
            x0_log = np.clip(best_global_x, free_lower_log, free_upper_log)

    result_local = least_squares(
        lambda x: _residuals_log(
            _log_to_linear(x),
            L_med,
            rho_med,
            n_layers,
            fixed_mask,
            fixed_values,
            strict_mode=strict_polish,
            threshold_pct=threshold_pct,
        ),
        x0=x0_log,
        bounds=(free_lower_log, free_upper_log),
        method="trf",
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=6000,
    )

    best_free_final = _log_to_linear(result_local.x)
    final_params = _merge_free_params(best_free_final, fixed_mask, fixed_values)
    best_rho = final_params[:n_layers]
    best_h = final_params[n_layers:]
    rmse, r2 = _fit_metrics(L_med, rho_med, best_rho, best_h)
    return list(best_rho), list(best_h), rmse, r2


def run_optimization(
    L_med,
    rho_med,
    initial_rho,
    initial_h,
    fixed_rho,
    fixed_h,
    use_global=False,
    try_alternate_layers: bool = False,
    *,
    strict_mode: bool = False,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
):
    """
    Ejecuta el proceso de optimización en dos pasos.
    Los parámetros libres se optimizan en escala log10 para estabilidad numérica.
    """
    configs = (
        _alternate_layer_configs(
            initial_rho,
            initial_h,
            fixed_rho,
            fixed_h,
            rho_med=np.asarray(rho_med, dtype=float),
        )
        if try_alternate_layers
        else [(initial_rho, initial_h, fixed_rho, fixed_h)]
    )

    best_result = None
    for rho_cfg, h_cfg, fr_cfg, fh_cfg in configs:
        if len(rho_cfg) != len(fr_cfg) or len(h_cfg) != len(fh_cfg):
            continue
        result = _optimize_single_configuration(
            L_med,
            rho_med,
            rho_cfg,
            h_cfg,
            fr_cfg,
            fh_cfg,
            use_global=use_global,
            strict_polish=False,
            threshold_pct=threshold_pct,
        )
        if best_result is None:
            best_result = result
            continue
        if strict_mode:
            rank_new = _strict_rank(L_med, rho_med, result[0], result[1], threshold_pct)
            rank_best = _strict_rank(L_med, rho_med, best_result[0], best_result[1], threshold_pct)
            if rank_new < rank_best:
                best_result = result
        elif result[3] > best_result[3]:
            best_result = result
    if best_result is None:
        best_result = _optimize_single_configuration(
            L_med,
            rho_med,
            initial_rho,
            initial_h,
            fixed_rho,
            fixed_h,
            use_global=use_global,
            strict_polish=False,
            threshold_pct=threshold_pct,
        )

    if strict_mode and best_result is not None:
        polished = _optimize_single_configuration(
            L_med,
            rho_med,
            best_result[0],
            best_result[1],
            fixed_rho,
            fixed_h,
            use_global=False,
            strict_polish=True,
            threshold_pct=threshold_pct,
        )
        if _strict_rank(L_med, rho_med, polished[0], polished[1], threshold_pct) < _strict_rank(
            L_med, rho_med, best_result[0], best_result[1], threshold_pct
        ):
            best_result = polished

    return best_result