from pathlib import Path
import argparse
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

MIN_OBS = 3
MIN_SHIFT = 0.06
MIN_EFFECT = 1.20
TEMP_SHIFT = 0.08
TEMP_EFFECT = 1.50

STABLE_START_MMDD=(6,1)
STABLE_END_MMDD=(9,15)

def mad(x):
    x=np.asarray(pd.Series(x).dropna(),float)
    if len(x)==0:
        return np.nan
    med=np.median(x)
    return float(np.median(np.abs(x-med)))

def load_hls(folder):
    frames=[]
    for y in range(2014,2026):
        p=Path(folder)/(
            f"SLI_HLS_ALLCAND_MarOct_{y}.csv"
        )
        if not p.exists():
            continue
        d=pd.read_csv(p)
        d["source_year"]=y
        d["source_sensor"]=d["sensor"]
        d["date"]=pd.to_datetime(d["date"])
        frames.append(d)
    if not frames:
        raise ValueError("No HLS yearly CSVs found.")
    return pd.concat(frames,ignore_index=True)

def calibrate_and_merge(hls):
    pairs_by_year={}
    pooled=[]

    for y in sorted(hls.source_year.unique()):
        g=hls[hls.source_year.eq(y)]
        L=g[g.source_sensor.eq("L30")][
            ["Lake_ID_num","date","mean_awei",
             "mndwi_water_fraction_valid"]
        ].rename(columns={
            "mean_awei":"aL",
            "mndwi_water_fraction_valid":"mL"
        })
        S=g[g.source_sensor.eq("S30")][
            ["Lake_ID_num","date","mean_awei",
             "mndwi_water_fraction_valid"]
        ].rename(columns={
            "mean_awei":"aS",
            "mndwi_water_fraction_valid":"mS"
        })
        pair=L.merge(
            S,on=["Lake_ID_num","date"]
        ).dropna()
        pairs_by_year[int(y)]=pair
        if len(pair):
            pooled.append(pair.assign(year=y))

    if not pooled:
        raise ValueError(
            "No same-day L30/S30 pairs available."
        )

    pooled=pd.concat(pooled,ignore_index=True)

    ga,gb=np.polyfit(pooled.aL,pooled.aS,1)
    gm,gmb=np.polyfit(pooled.mL,pooled.mS,1)

    calibration={}
    calrows=[]

    for y in sorted(hls.source_year.unique()):
        pair=pairs_by_year[int(y)]

        if len(pair)>=100:
            aa,ab=np.polyfit(
                pair.aL,pair.aS,1
            )
            ma,mb=np.polyfit(
                pair.mL,pair.mS,1
            )
            pooled_flag=False
        else:
            aa,ab,ma,mb=ga,gb,gm,gmb
            pooled_flag=True

        calibration[int(y)]=(aa,ab,ma,mb)

        calrows.append({
            "year":int(y),
            "same_day_lake_pairs":len(pair),
            "L30_to_S30_awei_slope":aa,
            "L30_to_S30_awei_intercept":ab,
            "L30_to_S30_mndwi_slope":ma,
            "L30_to_S30_mndwi_intercept":mb,
            "used_pooled_coefficients":
                pooled_flag
        })

    h=hls.copy()
    h["awei_s30eq"] = pd.to_numeric(
        h["mean_awei"],errors="coerce"
    )
    h["mndwi_s30eq"] = pd.to_numeric(
        h["mndwi_water_fraction_valid"],
        errors="coerce"
    )

    for y,(aa,ab,ma,mb) in calibration.items():
        m=h.source_year.eq(y) & \
          h.source_sensor.eq("L30")

        h.loc[m,"awei_s30eq"] = (
            aa*h.loc[m,"mean_awei"]+ab
        )

        h.loc[m,"mndwi_s30eq"] = (
            ma*h.loc[
                m,"mndwi_water_fraction_valid"
            ]+mb
        ).clip(0,1)

    sensor_keys=[
        "Lake_ID_num","Lake_ID","date",
        "source_year","source_sensor"
    ]

    agg=h.groupby(
        sensor_keys,as_index=False
    ).agg(
        awei_s30eq=("awei_s30eq","median"),
        mndwi_s30eq=("mndwi_s30eq","median"),
        awei_water_fraction=(
            "awei_water_fraction_valid","median"
        ),
        fmask_water_fraction=(
            "fmask_water_fraction_valid","median"
        ),
        valid_fraction=("valid_fraction","max")
    )

    date_keys=[
        "Lake_ID_num","Lake_ID","date",
        "source_year"
    ]

    agg["has_s30"]=agg.groupby(
        date_keys
    )["source_sensor"].transform(
        lambda x:(x=="S30").any()
    )

    use=agg[
        agg.source_sensor.eq("S30")
        | ~agg.has_s30
    ].copy()

    daily=use.groupby(
        date_keys,as_index=False
    ).agg(
        state_awei=("awei_s30eq","median"),
        state_mndwi=("mndwi_s30eq","median"),
        state_awei_water_fraction=(
            "awei_water_fraction","median"
        ),
        state_fmask_water_fraction=(
            "fmask_water_fraction","median"
        ),
        valid_fraction=("valid_fraction","max"),
        daily_source=(
            "source_sensor",
            lambda x:
                "S30" if (x=="S30").any()
                else "L30_calibrated"
        )
    )

    return daily,pd.DataFrame(calrows)

def stable_mask(date):
    m=date.dt.month
    d=date.dt.day
    after=(m>6)|((m==6)&(d>=1))
    before=(m<9)|((m==9)&(d<=15))
    return after & before

def make_stable_summary(daily):
    s=daily[stable_mask(daily.date)].copy()

    annual=s.groupby(
        ["Lake_ID_num","Lake_ID","source_year"],
        as_index=False
    ).agg(
        n_obs=("state_awei","count"),
        awei_med=("state_awei","median"),
        awei_mad=("state_awei",mad),
        mndwi_med=("state_mndwi","median"),
        awf_med=(
            "state_awei_water_fraction","median"
        ),
        valid_med=("valid_fraction","median")
    )
    return annual

def state_from_years(annual,lid,years):
    g=annual[
        annual.Lake_ID_num.eq(lid)
        & annual.source_year.isin(years)
        & annual.n_obs.ge(MIN_OBS)
    ].copy()

    if not len(g):
        return None

    return {
        "years":
            ",".join(map(str,sorted(
                g.source_year.astype(int).tolist()
            ))),
        "n_years":len(g),
        "n_obs_total":int(g.n_obs.sum()),
        "awei_med":float(
            g.awei_med.median()
        ),
        "awei_mad":float(
            np.nanmedian(g.awei_mad)
        ),
        "mndwi_med":float(
            g.mndwi_med.median()
        ),
        "awf_med":float(
            g.awf_med.median()
        )
    }

def persistent_timing(
    daily,lid,scan_start,scan_end,
    pre_state,post_state
):
    obs=daily[
        daily.Lake_ID_num.eq(lid)
        & daily.source_year.between(
            scan_start,scan_end
        )
    ].sort_values("date").copy().reset_index(drop=True)

    denom=post_state-pre_state

    if len(obs)==0 or not np.isfinite(denom) \
       or abs(denom)<1e-9:
        return {
            "timing_type":
                "unresolved"
        }

    obs["progress"] = (
        obs.state_awei-pre_state
    )/denom

    first_i=None
    support_n=np.nan
    support_fraction=np.nan

    for i in range(len(obs)):
        if obs.loc[i,"progress"]<0.65:
            continue

        nxt=obs.iloc[
            i:min(i+5,len(obs))
        ]

        if len(nxt)<2:
            continue

        frac=(nxt.progress>=0.55).mean()
        no_return=(
            nxt.iloc[
                :min(3,len(nxt))
            ].progress<=0.35
        ).sum()==0

        if frac>=0.75 and no_return \
           and obs.iloc[i:].progress.median()>=0.55:
            first_i=i
            support_n=len(nxt)
            support_fraction=frac
            break

    if first_i is None:
        return {
            "timing_type":
                "right_unresolved"
        }

    fp=obs.iloc[first_i]
    prelike=obs.iloc[:first_i]
    prelike=prelike[
        prelike.progress<=0.35
    ]

    if not len(prelike):
        return {
            "timing_type":
                "left_unresolved",
            "FirstPost":fp.date,
            "firstpost_progress":
                fp.progress
        }

    lp=prelike.iloc[-1]

    between=obs[
        obs.date.gt(lp.date)
        & obs.date.lt(fp.date)
    ]
    trans=between[
        between.progress.gt(0.35)
        & between.progress.lt(0.65)
    ]

    changed=obs[
        obs.date.gt(lp.date)
        & obs.progress.gt(0.35)
    ]

    first_changed=(
        changed.iloc[0].date
        if len(changed)
        else fp.date
    )

    changing=obs[
        obs.date.gt(lp.date)
        & obs.date.lt(fp.date)
        & obs.progress.gt(0.35)
        & obs.progress.lt(0.65)
    ]

    last_changing=(
        changing.iloc[-1].date
        if len(changing)
        else lp.date
    )

    wd=(fp.date-lp.date).days

    if lp.date.year==fp.date.year:
        if wd<=14:
            quality="high_le14d"
        elif wd<=30:
            quality="moderate_15_30d"
        else:
            quality="low_gt30d"

        typ=(
            "abrupt_resolved"
            if wd<=30 and len(trans)<=1
            else "progressive_within_season"
        )
    else:
        quality="interval_censored_cross_year"
        typ=(
            "progressive_interseason"
            if len(trans)>=2
            else "seasonally_censored"
        )

    return {
        "timing_type":typ,
        "timing_quality":quality,
        "LastPre":lp.date,
        "FirstPost":fp.date,
        "HLS_window_days":wd,
        "onset_FirstChanged":
            first_changed,
        "completion_LastChanging":
            last_changing,
        "n_transition_obs":
            len(trans),
        "post_support_n":
            support_n,
        "post_support_fraction":
            support_fraction,
        "lastpre_progress":
            lp.progress,
        "firstpost_progress":
            fp.progress
    }

def temporary_timing(
    obs,sign,baseline,amplitude
):
    obs=obs.sort_values(
        "date"
    ).copy().reset_index(drop=True)

    if len(obs)==0 or amplitude<=0:
        return {
            "temp_timing_type":
                "unresolved_excursion"
        }

    obs["excursion_progress"] = (
        sign*(obs.state_awei-baseline)
        / amplitude
    )

    first_i=None

    for i in range(len(obs)):
        if obs.loc[
            i,"excursion_progress"
        ]<0.65:
            continue

        nxt=obs.iloc[
            i:min(i+3,len(obs))
        ]

        if (
            nxt.excursion_progress>=0.55
        ).sum()>=2:
            first_i=i
            break

    if first_i is None:
        return {
            "temp_timing_type":
                "unresolved_excursion"
        }

    first=obs.iloc[first_i]

    before=obs.iloc[:first_i]
    normals=before[
        before.excursion_progress<=0.35
    ]
    last_normal=(
        normals.iloc[-1].date
        if len(normals)
        else pd.NaT
    )

    after=obs.iloc[first_i+1:]
    returns=after[
        after.excursion_progress<=0.35
    ]
    first_return=(
        returns.iloc[0].date
        if len(returns)
        else pd.NaT
    )

    excursion=obs[
        obs.excursion_progress>=0.55
    ]
    last_excursion=(
        excursion.iloc[-1].date
    )

    if pd.notna(last_normal) \
       and pd.notna(first_return):
        typ="temporary_resolved"
    elif pd.isna(last_normal):
        typ="temporary_left_censored"
    else:
        typ="temporary_right_censored"

    return {
        "temp_timing_type":typ,
        "TempLastNormalBefore":
            last_normal,
        "TempFirstExcursion":
            first.date,
        "TempLastExcursion":
            last_excursion,
        "TempFirstReturn":
            first_return
    }

def run_detector(
    hls_dir,candidate_csv,outdir
):
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)

    candidates=pd.read_csv(candidate_csv)
    hls=load_hls(hls_dir)

    daily,cal=calibrate_and_merge(hls)
    annual=make_stable_summary(daily)

    cal.to_csv(
        outdir/"01_HLS_sensor_calibration_v3.csv",
        index=False
    )
    daily.to_csv(
        outdir/"02_HLS_daily_state_MarOct_v3.csv",
        index=False
    )
    annual.to_csv(
        outdir/"03_HLS_stable_state_JunSep15_v3.csv",
        index=False
    )

    records=[]

    for _,e in candidates.iterrows():
        lid=int(e.Lake_ID_num)
        direction=e.direction
        sign=-1 if direction=="contraction" else 1

        pre_years=[
            int(e.run_start)-2,
            int(e.run_start)-1
        ]
        post_years=[
            int(e.run_end)+1,
            int(e.run_end)+2
        ]

        pre_years=[
            y for y in pre_years
            if 2014<=y<=2025
        ]
        post_years=[
            y for y in post_years
            if 2014<=y<=2025
        ]

        pre=state_from_years(
            annual,lid,pre_years
        )
        post=state_from_years(
            annual,lid,post_years
        )

        rec=e.to_dict()
        rec.update({
            "detector_version":
                "HLS_state_transition_v3",
            "hls_class":"unclassified",
            "state_transition_class":
                "unclassified"
        })

        if pre is not None:
            for k,v in pre.items():
                rec["pre_"+k]=v

        if post is not None:
            for k,v in post.items():
                rec["post_"+k]=v

        if pre is None or post is None:
            rec["hls_class"] = (
                "edge_or_insufficient_stable_state"
            )
            rec["state_transition_class"] = (
                rec["hls_class"]
            )
            rec["persistence_status"] = (
                "not_two_sided"
            )
            records.append(rec)
            continue

        signed_awei=sign*(
            post["awei_med"]
            - pre["awei_med"]
        )
        signed_mndwi=sign*(
            post["mndwi_med"]
            - pre["mndwi_med"]
        )

        noise=np.nanmedian([
            pre["awei_mad"],
            post["awei_mad"]
        ])+0.03

        effect=(
            signed_awei/noise
            if noise>0 else np.nan
        )

        rec.update({
            "signed_awei_shift":
                signed_awei,
            "signed_mndwi_shift":
                signed_mndwi,
            "baseline_noise":noise,
            "effect_score":effect
        })

        persistent=(
            signed_awei>=MIN_SHIFT
            and effect>=MIN_EFFECT
        )

        if persistent:
            rec["hls_class"] = (
                f"persistent_{direction}"
            )
            rec["state_transition_class"] = (
                rec["hls_class"]
            )
            rec["persistence_status"] = (
                "confirmed_two_sided"
            )

            rec.update(
                persistent_timing(
                    daily,lid,
                    int(e.timing_start_year),
                    int(e.timing_end_year),
                    pre["awei_med"],
                    post["awei_med"]
                )
            )

            tq=rec.get(
                "timing_quality",""
            )

            if effect>=2 \
               and signed_mndwi>=0.03 \
               and tq=="high_le14d":
                conf="high"
            elif effect>=1.5 \
                 and signed_mndwi>=0 \
                 and tq in {
                    "high_le14d",
                    "moderate_15_30d"
                 }:
                conf="medium"
            else:
                conf="low"

            rec["HLS_confidence"]=conf

        else:
            baseline=np.median([
                pre["awei_med"],
                post["awei_med"]
            ])

            target_obs=daily[
                daily.Lake_ID_num.eq(lid)
                & daily.source_year.between(
                    int(e.run_start),
                    int(e.run_end)
                )
            ].copy()

            if len(target_obs):
                extreme=(
                    target_obs.state_awei
                    .quantile(0.20)
                    if direction=="contraction"
                    else
                    target_obs.state_awei
                    .quantile(0.80)
                )
            else:
                extreme=np.nan

            temp_amp=(
                sign*(extreme-baseline)
                if pd.notna(extreme)
                else np.nan
            )

            temp_effect=(
                temp_amp/noise
                if pd.notna(temp_amp)
                and noise>0
                else np.nan
            )

            return_gap=abs(
                post["awei_med"]
                - pre["awei_med"]
            )

            rec.update({
                "temporary_amplitude":
                    temp_amp,
                "temporary_effect_score":
                    temp_effect,
                "pre_post_return_gap":
                    return_gap
            })

            is_temp=(
                pd.notna(temp_amp)
                and temp_amp>=TEMP_SHIFT
                and temp_effect>=TEMP_EFFECT
                and return_gap<=max(
                    0.08,0.60*temp_amp
                )
            )

            if is_temp:
                cls=(
                    "temporary_drawdown"
                    if direction=="contraction"
                    else "temporary_high_water"
                )

                rec["hls_class"]=cls
                rec["state_transition_class"]=cls
                rec["persistence_status"] = (
                    "returned_toward_pre_state"
                )
                rec["HLS_confidence"] = (
                    "high"
                    if temp_effect>=2.5
                    else "medium"
                )

                rec.update(
                    temporary_timing(
                        target_obs,sign,
                        baseline,temp_amp
                    )
                )
            else:
                if signed_awei>0:
                    cls=(
                        f"weak_or_ambiguous_"
                        f"{direction}"
                    )
                else:
                    cls=(
                        "GLAD_not_supported_"
                        "by_HLS"
                    )

                rec["hls_class"]=cls
                rec[
                    "state_transition_class"
                ]=cls
                rec[
                    "persistence_status"
                ]="not_confirmed"
                rec[
                    "HLS_confidence"
                ]="low"

        records.append(rec)

    cat=pd.DataFrame(records)

    cat["recovery_class"]="not_applicable"

    con=cat[
        cat.hls_class.eq(
            "persistent_contraction"
        )
    ].copy()

    con["event_date_sort"]=pd.to_datetime(
        con.get("FirstPost"),
        errors="coerce"
    )

    for idx,row in cat[
        cat.hls_class.eq(
            "persistent_expansion"
        )
    ].iterrows():

        lid=int(row.Lake_ID_num)

        exp_date=pd.to_datetime(
            row.get("FirstPost"),
            errors="coerce"
        )

        prior=con[
            con.Lake_ID_num.eq(lid)
        ].copy()

        if pd.notna(exp_date):
            prior=prior[
                prior.event_date_sort.notna()
                & prior.event_date_sort.lt(
                    exp_date
                )
            ]
        else:
            prior=prior[
                prior.run_end.lt(
                    row.run_start
                )
            ]

        if len(prior):
            cat.loc[
                idx,"recovery_class"
            ]="confirmed_refill_after_persistent_contraction"
        elif row.glad_context in {
            "post_contraction_recovery_candidate",
            "expansion_after_old_contraction_candidate"
        }:
            cat.loc[
                idx,"recovery_class"
            ]="possible_recovery_from_GLAD_history"
        else:
            cat.loc[
                idx,"recovery_class"
            ]="persistent_independent_expansion"

    cat.to_csv(
        outdir/
        "04_FINAL_HLS_event_catalog_v3.csv",
        index=False
    )

    persistent=cat[
        cat.hls_class.isin([
            "persistent_contraction",
            "persistent_expansion"
        ])
    ].copy()

    persistent.to_csv(
        outdir/
        "05_persistent_events_both_directions_v3.csv",
        index=False
    )

    temporary=cat[
        cat.hls_class.isin([
            "temporary_drawdown",
            "temporary_high_water"
        ])
    ].copy()

    temporary.to_csv(
        outdir/
        "06_temporary_events_both_directions_v3.csv",
        index=False
    )

    resolved=persistent[
        persistent.timing_quality.isin([
            "high_le14d",
            "moderate_15_30d"
        ])
    ].copy()

    resolved.to_csv(
        outdir/
        "07_timing_resolved_persistent_events_v3.csv",
        index=False
    )

    cat.groupby([
        "direction","magnitude_class",
        "hls_class"
    ]).size().reset_index(
        name="n"
    ).to_csv(
        outdir/
        "08_summary_class_direction_magnitude.csv",
        index=False
    )

    fp=pd.to_datetime(
        persistent["FirstPost"],
        errors="coerce"
    )

    month_summary=(
        persistent.assign(
            FirstPost_month=fp.dt.month,
            FirstPost_year=fp.dt.year
        )
        .groupby([
            "direction","FirstPost_year",
            "FirstPost_month"
        ]).size()
        .reset_index(name="n")
    )

    month_summary.to_csv(
        outdir/
        "09_persistent_event_month_summary.csv",
        index=False
    )

    print("\nHLS classes:")
    print(
        cat.hls_class.value_counts(
            dropna=False
        )
    )

    print("\nPersistent timing quality:")
    print(
        persistent.timing_quality.value_counts(
            dropna=False
        )
    )

    print("\nPersistent FirstPost months:")
    print(month_summary.to_string(index=False))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--hls-dir",required=True)
    ap.add_argument("--candidates",required=True)
    ap.add_argument("--outdir",
        default="HLS_v3_results")
    a=ap.parse_args()

    run_detector(
        a.hls_dir,a.candidates,a.outdir
    )
