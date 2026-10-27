from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'matched'
OUT.mkdir(parents=True, exist_ok=True)


def bootstrap_median(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(123)
    draws = np.median(rng.choice(values, (10000, len(values)), replace=True), axis=1)
    return np.quantile(draws, [0.025, 0.975])


def main():
    df = pd.read_csv(ROOT/'data/matched_climate.csv')
    df['event_week'] = pd.to_datetime(df.index_end).dt.strftime('%G-W%V')
    df['snowmelt_week2_mm'] = df.pre14_snowmelt_sum_mm - df.pre7_snowmelt_sum_mm
    cases = df[df.role.eq('case')].copy()
    controls = df[df.role.eq('historical_control')]
    if len(cases) != 268 or len(controls) != 533 or cases.stratum_id.duplicated().any():
        raise ValueError('Unexpected matched sample.')
    metrics = [('temperature (30 d)', 'pre30_t2m_mean_c', '°C'),
               ('precipitation (week 1)', 'pre7_prcp_sum_mm', 'mm'),
               ('snowmelt (week 2)', 'snowmelt_week2_mm', 'mm'),
               ('snowmelt (week 1)', 'pre7_snowmelt_sum_mm', 'mm'),
               ('runoff (week 1)', 'pre7_runoff_sum_mm', 'mm')]
    lake, weekly, summary = [], [], []
    for label, col, unit in metrics:
        med = controls.groupby('stratum_id')[col].median()
        x = cases[['stratum_id', 'Lake_ID', 'event_week', col]].rename(columns={col:'event_value'}).copy()
        x['control_median'] = x.stratum_id.map(med)
        x['delta'] = x.event_value - x.control_median
        if x.delta.isna().any():
            raise ValueError(f'Missing matched data: {label}')
        x['label'], x['unit'] = label, unit
        w = x.groupby('event_week', as_index=False).delta.median()
        w['label'], w['unit'] = label, unit
        if len(w) != 34:
            raise ValueError('Expected 34 event-week contrasts.')
        lo, hi = bootstrap_median(w.delta)
        summary.append([label, unit, len(w), w.delta.median(), lo, hi])
        lake.append(x)
        weekly.append(w)
    weeks = pd.concat(weekly, ignore_index=True)
    pd.concat(lake, ignore_index=True).to_csv(OUT/'lake_event_deltas.csv', index=False)
    weeks.to_csv(OUT/'Figure4A_eventweek_deltas.csv', index=False)
    pd.DataFrame(summary, columns=['label','unit','n_event_weeks','median_delta','CI_low','CI_high']).to_csv(OUT/'Figure4A_summary.csv', index=False)
    wide = weeks.pivot(index='event_week', columns='label', values='delta')
    pairs = [('temperature (30 d)', 'snowmelt (week 2)'),
             ('temperature (30 d)', 'snowmelt (week 1)'),
             ('snowmelt (week 2)', 'runoff (week 1)'),
             ('precipitation (week 1)', 'runoff (week 1)')]
    correlations = []
    for x, y in pairs:
        rho, p = spearmanr(wide[x], wide[y])
        correlations.append([x, y, len(wide), rho, p])
    pd.DataFrame(correlations, columns=['x','y','n_event_weeks','rho','p']).to_csv(OUT/'mechanism_correlations.csv', index=False)
    print(OUT)


if __name__ == '__main__':
    main()
