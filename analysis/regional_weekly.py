from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'regional'
OUT.mkdir(parents=True, exist_ok=True)


def standardize(df, values):
    anomaly = values - values.groupby(df.week_of_season).transform('mean')
    sd = anomaly.std(ddof=1)
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError('Exposure has no finite variation.')
    return anomaly / sd, sd


def fit(df, columns):
    rhs = ' + '.join(columns + ['C(week_of_season)', 'C(year)'])
    return smf.glm('events ~ ' + rhs, data=df, family=sm.families.Poisson(),
                   offset=np.log(df.at_risk)).fit()


def estimate(model, term):
    lo, hi = np.exp(model.conf_int().loc[term])
    return [np.exp(model.params[term]), lo, hi, model.pvalues[term]]


def main():
    df = pd.read_csv(ROOT / 'data' / 'regional_weekly.csv')
    if len(df) != 180 or df.duplicated(['year', 'week_of_season']).any():
        raise ValueError('Expected 180 unique region-weeks.')
    if not df.at_risk.gt(0).all() or df.events.sum() != 319:
        raise ValueError('Unexpected risk set or event count.')
    base = fit(df, [])
    specs = [('Runoff', 'runoff', 'runoff_sum_mm'),
             ('Snowmelt', 'snow', 'snowmelt_sum_mm'),
             ('Precipitation', 'precip', 'prcp_sum_mm'),
             ('Temperature', 'temp', 't2m_mean_c')]
    points, profiles, deviances, scales, lags = [], [], [], [], []
    for name, short, suffix in specs:
        for days in (7, 14, 30):
            col = f'pre{days}_{suffix}'
            z, sd = standardize(df, df[col])
            model = fit(df.assign(x=z), ['x'])
            profiles.append([name, f'{days} d', days, *estimate(model, 'x')])
            deviances.append([name, f'{days} d', days,
                              100 * (base.deviance-model.deviance)/base.deviance])
            d = df.loc[df.events.gt(0), ['year', 'week_of_season', 'events']].copy()
            d['value_z'] = z.loc[d.index]
            d['display_name'], d['short'] = name, short
            d['window'], d['source_col'] = f'{days} d', col
            points.append(d)
            scales.append([name, f'{days} d', sd, d.value_z.median()])
    for name, suffix in [('Runoff', 'runoff_sum_mm'), ('Snowmelt', 'snowmelt_sum_mm')]:
        values = [df[f'pre7_{suffix}'],
                  df[f'pre14_{suffix}'] - df[f'pre7_{suffix}'],
                  df[f'pre30_{suffix}'] - df[f'pre14_{suffix}']]
        d = df.copy()
        for i, value in enumerate(values, 1):
            d[f'x{i}'] = standardize(df, value)[0]
        joint = fit(d, ['x1', 'x2', 'x3'])
        labels = [('Week 1', '1–7 d'), ('Week 2', '8–14 d'), ('Weeks 3–4', '15–30 d')]
        for i, (label, days_label) in enumerate(labels, 1):
            for kind, model in [('Joint three-bin model', joint),
                                ('Separate-bin model', fit(d, [f'x{i}']))]:
                lags.append([name, label, days_label, kind, *estimate(model, f'x{i}')])
    pd.concat(points).to_csv(OUT/'Figure3A_eventweek_standardized_sameweek_anomalies.csv', index=False)
    pd.DataFrame(profiles, columns=['display_name','window','days','IRR','CI_low','CI_high','p']).to_csv(OUT/'Figure3B_IRR_profiles.csv', index=False)
    pd.DataFrame(deviances, columns=['display_name','window','days','added_deviance_pct']).to_csv(OUT/'Figure3C_added_deviance.csv', index=False)
    pd.DataFrame(lags, columns=['display_name','period_label','days_label','model','IRR','CI_low','CI_high','p']).to_csv(OUT/'Figure3D_lag_bin_models.csv', index=False)
    pd.DataFrame(scales, columns=['display_name','window','sd','median_eventweek_z']).to_csv(OUT/'Figure3_metric_sds.csv', index=False)
    print(OUT)


if __name__ == '__main__':
    main()
