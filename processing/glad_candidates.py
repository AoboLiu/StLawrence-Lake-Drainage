import argparse
import numpy as np
import pandas as pd

def build_candidates(csv_path):
    annual = pd.read_csv(csv_path)
    pw = annual.pivot(index="Lake_ID_num", columns="year",
                      values="weighted_area_ha")
    attrs = (
        annual.sort_values("year")
        .groupby("Lake_ID_num")
        .first()[["Lake_ID","reference_area_ha",
                  "core_area_ha","ownership_area_ha"]]
        .reset_index()
    )

    records = []
    for t in range(2016, 2025):
        pre_years = [y for y in [t-3,t-2,t-1] if y in pw.columns]
        post_years = [y for y in [t,t+1,t+2] if y in pw.columns]

        pre = pw[pre_years].median(axis=1)
        post = pw[post_years].median(axis=1)
        delta = post - pre
        pct = delta / pre.replace(0, np.nan) * 100.0

        for lid in pw.index[pct <= -20.0]:
            records.append(dict(
                Lake_ID_num=int(lid), flag_year=t,
                direction="contraction",
                pre_median_ha=float(pre[lid]),
                post_median_ha=float(post[lid]),
                delta_ha=float(delta[lid]),
                delta_pct=float(pct[lid]),
                post_year_count=len(post_years)
            ))

        for lid in pw.index[pct >= 20.0]:
            records.append(dict(
                Lake_ID_num=int(lid), flag_year=t,
                direction="expansion",
                pre_median_ha=float(pre[lid]),
                post_median_ha=float(post[lid]),
                delta_ha=float(delta[lid]),
                delta_pct=float(pct[lid]),
                post_year_count=len(post_years)
            ))

    raw = pd.DataFrame(records)
    collapsed = []

    for (lid, direction), sub in raw.groupby(
        ["Lake_ID_num","direction"]
    ):
        sub = sub.sort_values("flag_year")
        runs, current, last = [], [], None

        for _, r in sub.iterrows():
            y = int(r["flag_year"])
            if last is None or y <= last + 1:
                current.append(r)
            else:
                runs.append(pd.DataFrame(current))
                current = [r]
            last = y

        if current:
            runs.append(pd.DataFrame(current))

        for run in runs:
            strongest = run.loc[
                run["delta_pct"].abs().idxmax()
            ].copy()

            strongest["run_start"] = int(
                run["flag_year"].min()
            )
            strongest["run_end"] = int(
                run["flag_year"].max()
            )
            strongest["candidate_year"] = int(
                strongest["flag_year"]
            )
            strongest["n_flagged_years"] = len(run)
            collapsed.append(strongest)

    cand = pd.DataFrame(collapsed).drop(
        columns=["flag_year"]
    ).merge(attrs, on="Lake_ID_num", how="left")

    cand["abs_delta_pct"] = cand["delta_pct"].abs()
    cand["magnitude_class"] = np.where(
        cand["abs_delta_pct"] >= 50,
        "major_ge50",
        "moderate_20_50"
    )
    cand["provisional_recent"] = (
        cand["post_year_count"] < 3
    )

    cand["timing_start_year"] = (
        cand["run_start"] - 1
    ).clip(lower=2014)

    cand["timing_end_year"] = (
        cand["run_end"] + 1
    ).clip(upper=2025)

    cand["extract_start_year"] = (
        cand["run_start"] - 2
    ).clip(lower=2014)

    cand["extract_end_year"] = (
        cand["run_end"] + 2
    ).clip(upper=2025)

    cand["glad_context"] = np.where(
        cand["direction"].eq("contraction"),
        "contraction_candidate",
        "independent_expansion_candidate"
    )
    cand["lag_from_prior_contraction_run_yr"] = np.nan

    for idx, r in cand[
        cand["direction"].eq("expansion")
    ].iterrows():
        prev = cand[
            cand["Lake_ID_num"].eq(r["Lake_ID_num"])
            & cand["direction"].eq("contraction")
            & cand["run_end"].lt(r["run_start"])
        ]
        if len(prev):
            lag = int(
                r["run_start"] - prev["run_end"].max()
            )
            cand.loc[
                idx,"lag_from_prior_contraction_run_yr"
            ] = lag
            cand.loc[idx,"glad_context"] = (
                "post_contraction_recovery_candidate"
                if lag <= 4
                else "expansion_after_old_contraction_candidate"
            )

    cand = cand.sort_values(
        ["run_start","Lake_ID_num",
         "direction","abs_delta_pct"],
        ascending=[True,True,True,False]
    ).reset_index(drop=True)

    cand.insert(
        0, "Candidate_ID",
        [f"GLADV3_{i+1:05d}" for i in range(len(cand))]
    )
    return cand

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("annual_csv")
    ap.add_argument("--output",
        default="SLI_GLAD_candidate_runs_2016_2024_v3_1.csv")
    args = ap.parse_args()

    out = build_candidates(args.annual_csv)
    out.to_csv(args.output,index=False)

    print("Candidate runs:",len(out))
    print(out.groupby(
        ["direction","magnitude_class"]
    ).size())
