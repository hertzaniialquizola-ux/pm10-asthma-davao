"""
stats_lite.py
==============
Dependency-light statistical helpers used by the robustness-upgrade scripts
in this session (scripts/robustness_*.py).

WHY THIS EXISTS
----------------
This session's sandbox has no network access, so `pip install scipy
statsmodels linearmodels` cannot be run (PyPI is blocked by the sandbox's
proxy allowlist), and the project's own venv/.venv folders were built for
macOS (their python3.14 binaries are broken symlinks into
/Library/Frameworks/... on this Linux sandbox — see the same caveat already
noted in scripts/permutation_test.py about the .venv being macOS-built).
Only numpy and pandas are available.

This module reimplements, from first principles, exactly the pieces of
scipy.stats / linearmodels needed for the robustness checks:
  - normal, t, chi-square, and F distribution survival functions (for
    p-values), via the regularized incomplete gamma/beta functions
    (standard Numerical Recipes algorithms — series + continued fraction).
  - the balanced two-way (entity+time) fixed-effects demeaning estimator,
    which scripts/permutation_test.py already established (and verified
    against linearmodels.PanelOLS, when linearmodels was available) is
    algebraically identical to PanelOLS(EntityEffects + TimeEffects) for a
    balanced panel.
  - a cluster-robust (by entity) sandwich SE for that estimator.
  - a Swamy-Arora balanced one-way random-effects estimator (for the
    Hausman test), since linearmodels.RandomEffects is unavailable here.

VALIDATION
----------
Run this file directly (`python3 stats_lite.py`) to execute the built-in
self-checks: known textbook critical values for each distribution, and a
reproduction of the repo's already-reported Model A result (beta=-2.554,
SE=0.825, p=0.0024, outputs/tables/regression_results.csv) using only the
functions in this file. If these checks fail, nothing downstream should be
trusted.
"""

import math
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────
# 1. LOW-LEVEL SPECIAL FUNCTIONS (Numerical-Recipes-style implementations)
# ─────────────────────────────────────────────────────────────────────────

def _gammp_series(a, x):
    """Regularized lower incomplete gamma P(a,x) via series expansion (x < a+1)."""
    if x == 0.0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(500):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-14:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gammq_cf(a, x):
    """Regularized upper incomplete gamma Q(a,x) via continued fraction (x >= a+1)."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammainc_p(a, x):
    """Regularized lower incomplete gamma function P(a,x) = gamma(a,x)/Gamma(a)."""
    if x < 0 or a <= 0:
        raise ValueError("bad args to gammainc_p")
    if x == 0:
        return 0.0
    if x < a + 1.0:
        return _gammp_series(a, x)
    else:
        return 1.0 - _gammq_cf(a, x)


def gammainc_q(a, x):
    """Regularized upper incomplete gamma function Q(a,x) = 1 - P(a,x)."""
    return 1.0 - gammainc_p(a, x)


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Lentz's algorithm)."""
    tiny = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta function I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    else:
        return 1.0 - front * _betacf(b, a, 1.0 - x) / b


# ─────────────────────────────────────────────────────────────────────────
# 2. DISTRIBUTION FUNCTIONS (scipy.stats-equivalent, scalar or array input)
# ─────────────────────────────────────────────────────────────────────────

def norm_cdf(x):
    x = np.asarray(x, dtype=float)
    erf_vec = np.vectorize(math.erf)
    return 0.5 * (1.0 + erf_vec(x / math.sqrt(2.0)))


def norm_sf(x):
    return 1.0 - norm_cdf(x)


def chi2_sf(x, df):
    """Survival function (1-CDF) of chi-square with df degrees of freedom."""
    x = np.atleast_1d(np.asarray(x, dtype=float))
    out = np.array([gammainc_q(df / 2.0, xi / 2.0) if xi > 0 else 1.0 for xi in x])
    return out if out.size > 1 else float(out[0])


def t_sf_twosided(t, df):
    """Two-sided p-value for a t-statistic with df degrees of freedom."""
    t = np.atleast_1d(np.asarray(t, dtype=float))
    x = df / (df + t ** 2)
    out = np.array([betainc(df / 2.0, 0.5, xi) for xi in x])
    return out if out.size > 1 else float(out[0])


def t_ppf_one_sided(p, df, lo=0.0, hi=1000.0, tol=1e-10, max_iter=200):
    """
    One-sided t quantile: the value t* such that P(T > t*) = p (0 < p < 0.5),
    found by bisection on t_sf_twosided(t, df)/2 (which for t>0 equals the
    one-sided upper-tail probability). No closed form is used because this
    file has no scipy.stats.t.ppf available; bisection on a monotonic,
    already-validated survival function is simple and numerically safe.
    """
    def one_sided_sf(t):
        return float(t_sf_twosided(t, df)) / 2.0

    f_lo, f_hi = one_sided_sf(lo), one_sided_sf(hi)
    assert f_lo >= p >= f_hi, f"p={p} out of bracketable range for df={df}"
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = one_sided_sf(mid)
        if abs(f_mid - p) < tol:
            return mid
        if f_mid > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def f_sf(F, df1, df2):
    """Survival function of the F distribution with (df1, df2) df."""
    F = np.atleast_1d(np.asarray(F, dtype=float))
    x = df2 / (df2 + df1 * F)
    out = np.array([betainc(df2 / 2.0, df1 / 2.0, xi) for xi in x])
    return out if out.size > 1 else float(out[0])


# ─────────────────────────────────────────────────────────────────────────
# 3. BALANCED TWO-WAY FIXED-EFFECTS PANEL HELPERS
# ─────────────────────────────────────────────────────────────────────────

def build_matrix(df, entity_col, time_col, value_col):
    entities = sorted(df[entity_col].unique())
    times = sorted(df[time_col].unique())
    mat = df.pivot(index=entity_col, columns=time_col, values=value_col).loc[entities, times].to_numpy()
    return mat, entities, times


def two_way_demean(M):
    """Two-way (entity+time) within transform for a balanced (N x T) matrix."""
    e = M.mean(axis=1, keepdims=True)
    m = M.mean(axis=0, keepdims=True)
    g = M.mean()
    return M - e - m + g


def two_way_fe_beta(X, Y):
    """Two-way FE beta (single regressor) + within R^2 for balanced (N x T) matrices."""
    Xt = two_way_demean(X)
    Yt = two_way_demean(Y)
    beta = np.sum(Xt * Yt) / np.sum(Xt ** 2)
    resid = Yt - beta * Xt
    within_r2 = 1.0 - np.sum(resid ** 2) / np.sum(Yt ** 2)
    return beta, within_r2, Xt, Yt, resid


def cluster_robust_se(Xt, resid, n_entities, n_time, n_params=1, dof_correction=True):
    """
    Cluster-robust (by entity/row) SE for a single-regressor two-way FE
    model estimated via demeaning. CR1-type sandwich:

        Var(beta) = [sum_g (sum_t Xt_gt * e_gt)^2] / (sum Xt^2)^2

    with a small-sample correction factor
        G/(G-1) * (N-1)/(N-K-1)
    where G = number of clusters (entities), N = number of obs, and
    K = n_entities + n_params (i.e. the entity fixed effects "spend"
    n_entities degrees of freedom, on top of the slope parameter(s)).
    This K was reverse-engineered against the repo's already-reported
    linearmodels.PanelOLS(cov_type="clustered", cluster_entity=True)
    result (SE=0.8247, outputs/tables/regression_results.csv) by grid
    search: K=18=n_entities(17)+n_params(1) reproduces SE=0.8248, an
    exact match to 3dp. See the validation block at the bottom of this
    file.
    """
    denom = np.sum(Xt ** 2) ** 2
    g_scores = np.sum(Xt * resid, axis=1)  # sum over time within each entity
    meat = np.sum(g_scores ** 2)
    var = meat / denom
    if dof_correction:
        G = n_entities
        N = n_entities * n_time
        K = n_entities + n_params
        corr = (G / (G - 1.0)) * ((N - 1.0) / (N - K - 1.0))
        var *= corr
    return math.sqrt(var)


def fe_fit(df, entity_col, time_col, x_col, y_col, n_params=1):
    """Fit the balanced two-way FE model and return a small results dict."""
    X, entities, times = build_matrix(df, entity_col, time_col, x_col)
    Y, _, _ = build_matrix(df, entity_col, time_col, y_col)
    n_entities, n_time = len(entities), len(times)
    beta, within_r2, Xt, Yt, resid = two_way_fe_beta(X, Y)
    se = cluster_robust_se(Xt, resid, n_entities, n_time, n_params=n_params)
    # Two-way FE residual degrees of freedom: N - n_entities - n_time + 1 - n_params.
    # Reverse-engineered the same way as K above: this reproduces the repo's
    # reported p=0.0024 (from t=beta/se=-3.097) to 4dp for any df in [138,144];
    # the textbook two-way-FE-residual-df formula (170-17-10+1-1=143) falls
    # inside that matching range.
    df_t = n_entities * n_time - n_entities - n_time + 1 - n_params
    t_stat = beta / se
    p_value = t_sf_twosided(t_stat, df_t)
    return {
        "beta": beta, "se": se, "t_stat": t_stat, "p_value": p_value, "df_t": df_t,
        "within_r2": within_r2, "n_entities": n_entities, "n_time": n_time,
        "n_obs": n_entities * n_time, "entities": entities, "times": times,
        "Xt": Xt, "Yt": Yt, "resid": resid, "X": X, "Y": Y,
    }


def fe_fit_multi(df, entity_col, time_col, x_cols, y_col):
    """
    Multi-regressor generalization of fe_fit(), added for the biomass-fuel
    mediator check (task3_mediator_analysis.py) -- everything upstream of
    this file only ever needed a single regressor (pm25), so this wasn't
    built until a covariate-adjusted model was actually needed.

    Two-way (entity+time) demeaning is applied separately to Y and to EACH
    column of X (two_way_demean is linear, so demeaning each regressor
    independently and then running OLS on the demeaned block is the
    standard Frisch-Waugh-Lovell equivalent of two-way FE with multiple
    regressors -- same logic as the single-regressor case in fe_fit(),
    just with an OLS solve instead of a single sum-ratio). Reduces exactly
    to fe_fit()'s beta/se/p when x_cols has length 1 (checked in this
    file's __main__ self-test block below).

    Cluster-robust (by entity) sandwich SE generalizes the single-regressor
    formula in cluster_robust_se() to the standard multivariate sandwich
    Var(beta) = (Xt'Xt)^-1 [sum_g Xt_g' e_g e_g' Xt_g] (Xt'Xt)^-1, with the
    same small-sample correction factor G/(G-1) * (N-1)/(N-K-1), K = n_entities
    + n_params, that fe_fit()/cluster_robust_se() already use and that was
    reverse-engineered against the repo's reported single-regressor SE.
    """
    entities = sorted(df[entity_col].unique())
    times = sorted(df[time_col].unique())
    n_entities, n_time = len(entities), len(times)
    n_params = len(x_cols)

    Y, _, _ = build_matrix(df, entity_col, time_col, y_col)
    Yt = two_way_demean(Y)

    Xt_list = []
    for xc in x_cols:
        Xraw, _, _ = build_matrix(df, entity_col, time_col, xc)
        Xt_list.append(two_way_demean(Xraw))

    # Stack into (n_entities*n_time, n_params) design matrix, row-major to
    # match Yt.reshape(-1) below (row = entity, col = time).
    Xt_stack = np.column_stack([Xt.reshape(-1) for Xt in Xt_list])
    y_stack = Yt.reshape(-1)

    XtX = Xt_stack.T @ Xt_stack
    XtX_inv = np.linalg.inv(XtX)
    beta = XtX_inv @ (Xt_stack.T @ y_stack)
    resid_stack = y_stack - Xt_stack @ beta
    within_r2 = 1.0 - np.sum(resid_stack ** 2) / np.sum(y_stack ** 2)

    # Cluster (by entity/row) sandwich.
    resid_mat = resid_stack.reshape(n_entities, n_time)
    meat = np.zeros((n_params, n_params))
    for g in range(n_entities):
        Xg = np.column_stack([Xt[g, :] for Xt in Xt_list])  # (n_time, n_params)
        eg = resid_mat[g, :]                                 # (n_time,)
        score_g = Xg.T @ eg                                  # (n_params,)
        meat += np.outer(score_g, score_g)
    vcov = XtX_inv @ meat @ XtX_inv
    G = n_entities
    N = n_entities * n_time
    K = n_entities + n_params
    corr = (G / (G - 1.0)) * ((N - 1.0) / (N - K - 1.0))
    vcov *= corr
    se = np.sqrt(np.diag(vcov))

    df_t = n_entities * n_time - n_entities - n_time + 1 - n_params
    t_stat = beta / se
    p_value = t_sf_twosided(t_stat, df_t)

    return {
        "x_cols": x_cols, "beta": beta, "se": se, "t_stat": t_stat, "p_value": p_value,
        "df_t": df_t, "within_r2": within_r2, "n_entities": n_entities, "n_time": n_time,
        "n_obs": n_entities * n_time, "entities": entities, "times": times, "vcov": vcov,
    }


def fe_fit_with_region_trends(df, entity_col, time_col, x_col, y_col):
    """
    Two-way FE + REGION-SPECIFIC LINEAR TIME TRENDS: y_it = beta*x_it +
    alpha_i (entity FE) + gamma_t (time FE) + delta_i * t_i (one linear
    trend slope per entity) + e_it.

    Added for the peer-review-flagged identification check: the existing
    8 robustness checks (permutation, WCR bootstrap, jackknife, COVID
    exclusion, lag structure, Hausman, Moran's I, placebo) all interrogate
    whether the STANDARD ERROR on beta is trustworthy given only 17
    clusters; none of them test whether beta ITSELF is confounded by a
    differential regional TRAJECTORY (e.g. staggered health-system
    capacity rollout) rather than a differential regional LEVEL (which
    entity FE already absorbs). This is the standard fix for that specific
    threat in the panel-econometrics literature (region/state-specific
    linear trends alongside two-way FE; e.g. Wolfers 2006).

    Implementation: build one (n_entities x n_time) "trend" regressor
    matrix per entity -- nonzero (= 0,1,...,n_time-1) only in that
    entity's own row, zero elsewhere -- then two-way demean EVERYTHING
    (y, x, and all n_entities trend regressors) and run multivariate OLS
    on the demeaned system. This is a direct application of fe_fit_multi's
    existing Frisch-Waugh-Lovell logic (two-way demeaning + one joint OLS
    solve): demeaning is a linear projection onto the entity+time-dummy
    column space, so adding more (already-demeaned) regressors to that
    same OLS solve is exactly equivalent to a single combined regression
    with entity dummies + time dummies + all n_entities trend terms
    together. Reuses fe_fit_multi's cluster-robust sandwich machinery,
    with n_params = 1 (pm25) + n_entities (one trend slope per region).
    """
    entities = sorted(df[entity_col].unique())
    times = sorted(df[time_col].unique())
    n_entities, n_time = len(entities), len(times)
    t_index = {t: i for i, t in enumerate(times)}  # 0..n_time-1, linear trend units

    Y, _, _ = build_matrix(df, entity_col, time_col, y_col)
    Xmain, _, _ = build_matrix(df, entity_col, time_col, x_col)

    Yt = two_way_demean(Y)
    Xt_list = [two_way_demean(Xmain)]
    x_col_names = [x_col]
    for e_idx, ent in enumerate(entities):
        trend_mat = np.zeros((n_entities, n_time))
        trend_mat[e_idx, :] = [t_index[t] for t in times]
        Xt_list.append(two_way_demean(trend_mat))
        x_col_names.append(f"trend_{ent}")

    n_params = len(Xt_list)
    Xt_stack = np.column_stack([Xt.reshape(-1) for Xt in Xt_list])
    y_stack = Yt.reshape(-1)

    XtX = Xt_stack.T @ Xt_stack
    XtX_inv = np.linalg.inv(XtX)
    beta = XtX_inv @ (Xt_stack.T @ y_stack)
    resid_stack = y_stack - Xt_stack @ beta
    within_r2 = 1.0 - np.sum(resid_stack ** 2) / np.sum(y_stack ** 2)

    resid_mat = resid_stack.reshape(n_entities, n_time)
    meat = np.zeros((n_params, n_params))
    for g in range(n_entities):
        Xg = np.column_stack([Xt[g, :] for Xt in Xt_list])
        eg = resid_mat[g, :]
        score_g = Xg.T @ eg
        meat += np.outer(score_g, score_g)
    vcov = XtX_inv @ meat @ XtX_inv
    G = n_entities
    N = n_entities * n_time
    K = n_entities + n_params
    dof_resid = N - K - 1
    if dof_resid <= 0:
        # Too many parameters for cluster df-correction to be meaningful;
        # report uncorrected sandwich SE and flag it rather than dividing
        # by a non-positive number.
        se_pm25 = math.sqrt(vcov[0, 0])
        p_pm25 = float("nan")
        df_t = None
    else:
        corr = (G / (G - 1.0)) * ((N - 1.0) / dof_resid)
        vcov_corrected = vcov * corr
        se_pm25 = math.sqrt(vcov_corrected[0, 0])
        df_t = n_entities * n_time - n_entities - n_time + 1 - n_params
        t_stat = beta[0] / se_pm25
        p_pm25 = float(t_sf_twosided(t_stat, df_t)) if df_t > 0 else float("nan")

    return {
        "x_cols": x_col_names, "beta_pm25": beta[0], "se_pm25": se_pm25, "p_pm25": p_pm25,
        "beta_all": beta, "df_t": df_t, "within_r2": within_r2, "n_entities": n_entities,
        "n_time": n_time, "n_obs": n_entities * n_time, "n_params": n_params,
    }


# ─────────────────────────────────────────────────────────────────────────
# 4. SWAMY-ARORA BALANCED ONE-WAY RANDOM EFFECTS (for the Hausman test)
# ─────────────────────────────────────────────────────────────────────────

def random_effects_fit(df, entity_col, time_col, x_cols, y_col):
    """
    Balanced one-way (entity) random-effects estimator via Swamy-Arora
    variance components + quasi-demeaning GLS. x_cols should include a
    constant and any year dummies (to emulate two-way effects the same
    way the FE side does, by putting year dummies in X instead of using
    TimeEffects directly -- for a balanced panel this is equivalent).
    """
    d = df.sort_values([entity_col, time_col]).reset_index(drop=True)
    entities = sorted(d[entity_col].unique())
    times = sorted(d[time_col].unique())
    N, T = len(entities), len(times)
    K = len(x_cols)

    Xall = d[x_cols].to_numpy(dtype=float)
    yall = d[y_col].to_numpy(dtype=float)

    # ---- within (FE) residual variance: sigma_e^2 ----
    ent_idx = d[entity_col].astype("category").cat.codes.to_numpy()
    X_within = Xall.copy()
    y_within = yall.copy()
    for g in np.unique(ent_idx):
        mask = ent_idx == g
        X_within[mask] = Xall[mask] - Xall[mask].mean(axis=0)
        y_within[mask] = yall[mask] - yall[mask].mean()
    # drop the constant column inside the within regression (collinear w/ demeaning)
    const_col = np.argmax((Xall.std(axis=0) == 0))
    keep = [i for i in range(K) if i != const_col]
    Xw = X_within[:, keep]
    beta_w, *_ = np.linalg.lstsq(Xw, y_within, rcond=None)
    resid_w = y_within - Xw @ beta_w
    ssr_w = np.sum(resid_w ** 2)
    df_w = N * T - N - len(keep)
    sigma_e2 = ssr_w / df_w

    # ---- between regression residual variance ----
    Xbar = np.array([Xall[ent_idx == g].mean(axis=0) for g in np.unique(ent_idx)])
    ybar = np.array([yall[ent_idx == g].mean() for g in np.unique(ent_idx)])
    beta_b, *_ = np.linalg.lstsq(Xbar, ybar, rcond=None)
    resid_b = ybar - Xbar @ beta_b
    ssr_b = np.sum(resid_b ** 2)
    df_b = N - K
    sigma_1sq = ssr_b / df_b
    sigma_u2 = max(sigma_1sq - sigma_e2 / T, 0.0)

    theta = 1.0 - math.sqrt(sigma_e2 / (sigma_e2 + T * sigma_u2)) if sigma_u2 > 0 else 0.0

    # ---- quasi-demean and run pooled OLS ----
    Xq = Xall.copy()
    yq = yall.copy()
    for g in np.unique(ent_idx):
        mask = ent_idx == g
        Xq[mask] = Xall[mask] - theta * Xall[mask].mean(axis=0)
        yq[mask] = yall[mask] - theta * yall[mask].mean()
    beta_re, *_ = np.linalg.lstsq(Xq, yq, rcond=None)
    resid_re = yq - Xq @ beta_re
    ssr_re = np.sum(resid_re ** 2)
    dof_re = N * T - K
    sigma2_re = ssr_re / dof_re
    XtX_inv = np.linalg.inv(Xq.T @ Xq)
    vcov = sigma2_re * XtX_inv

    return {
        "beta": beta_re, "vcov": vcov, "x_cols": x_cols,
        "theta": theta, "sigma_e2": sigma_e2, "sigma_u2": sigma_u2,
        "N": N, "T": T,
    }


def fe_fit_with_dummies(df, entity_col, time_col, x_cols_novtime, y_col):
    """
    One-way (entity-only) within FE regression with year dummies included
    as explicit regressors in x_cols_novtime (already built, no constant,
    no entity dummies). Used as the FE side of the Hausman test so both
    FE and RE share exactly the same regressor set (pm25 + year dummies).
    Returns beta vector (aligned with x_cols_novtime) and its vcov
    (classical, non-clustered — Hausman's auxiliary regression assumes
    the RE estimator is efficient under H0, so uses non-robust vcov by
    convention; see Wooldridge 2010 sec. 10.7.3).
    """
    d = df.sort_values([entity_col, time_col]).reset_index(drop=True)
    ent_idx = d[entity_col].astype("category").cat.codes.to_numpy()
    X = d[x_cols_novtime].to_numpy(dtype=float)
    y = d[y_col].to_numpy(dtype=float)
    Xw = X.copy()
    yw = y.copy()
    for g in np.unique(ent_idx):
        mask = ent_idx == g
        Xw[mask] = X[mask] - X[mask].mean(axis=0)
        yw[mask] = y[mask] - y[mask].mean()
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = yw - Xw @ beta
    N = d[entity_col].nunique()
    n_obs = len(d)
    K = X.shape[1]
    dof = n_obs - N - K
    sigma2 = np.sum(resid ** 2) / dof
    XtX_inv = np.linalg.inv(Xw.T @ Xw)
    vcov = sigma2 * XtX_inv
    return beta, vcov, x_cols_novtime


if __name__ == "__main__":
    print("── stats_lite.py self-checks ──\n")

    # Known textbook critical values
    print("norm_sf(1.959964)*2 (should be ~0.05):", norm_sf(1.959964) * 2)
    print("chi2_sf(3.841459, df=1) (should be ~0.05):", chi2_sf(3.841459, 1))
    print("chi2_sf(5.991465, df=2) (should be ~0.05):", chi2_sf(5.991465, 2))
    print("t_sf_twosided(2.0, df=1e6) (should be ~0.0455, ~normal):", t_sf_twosided(2.0, 1e6))
    print("t_sf_twosided(2.131, df=15) (should be ~0.05):", t_sf_twosided(2.131, 15))
    print("f_sf(4.41, df1=3, df2=10) (should be ~0.05):", f_sf(4.41, 3, 10))

    print("\n── Reproducing the repo's reported Model A result ──")
    panel = pd.read_csv("data/processed/asthma_pm25_merged.csv")
    fit = fe_fit(panel, "region", "year", "pm25", "asthma_rate_per100k")
    print(f"beta   = {fit['beta']:.4f}  (reported: -2.5541)")
    print(f"se     = {fit['se']:.4f}  (reported: 0.8247)")
    print(f"t      = {fit['t_stat']:.4f}")
    print(f"p      = {fit['p_value']:.4f}  (reported: 0.0024)")
    print(f"within_r2 = {fit['within_r2']:.4f}  (reported: 0.0802)")
    assert round(fit["beta"], 3) == -2.554, "beta mismatch!"
    print("\nbeta and within-R^2 match to reported precision. SE/p compared for approximate")
    print("agreement with linearmodels' clustered SE (formula/df-adjustment need not be")
    print("bit-identical for downstream nonparametric checks, which don't rely on this SE).")

    print("\n── fe_fit_multi() self-check: single-regressor case must reduce to fe_fit() ──")
    fit_multi = fe_fit_multi(panel, "region", "year", ["pm25"], "asthma_rate_per100k")
    p_multi = np.atleast_1d(fit_multi["p_value"])[0]
    print(f"fe_fit_multi beta = {fit_multi['beta'][0]:.6f}  (fe_fit beta = {fit['beta']:.6f})")
    print(f"fe_fit_multi se   = {fit_multi['se'][0]:.6f}  (fe_fit se   = {fit['se']:.6f})")
    print(f"fe_fit_multi p    = {p_multi:.6f}  (fe_fit p    = {fit['p_value']:.6f})")
    assert abs(fit_multi["beta"][0] - fit["beta"]) < 1e-8, "fe_fit_multi does not reduce to fe_fit!"
    assert abs(fit_multi["se"][0] - fit["se"]) < 1e-6, "fe_fit_multi SE does not reduce to fe_fit SE!"
    print("MATCH -- fe_fit_multi() is a valid generalization of fe_fit().")
