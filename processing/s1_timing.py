from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def refine(manifest, tracks, observations):
    tracks = tracks.copy()
    tracks['shift'] = np.hypot(tracks.post_vv_db-tracks.pre_vv_db,
                               tracks.post_vh_db-tracks.pre_vh_db)
    tracks['eligible'] = tracks.n_pre_context.ge(1) & tracks.n_post_context.ge(1)
    tracks['strong'] = tracks.eligible & tracks['shift'].ge(1.5)
    obs = observations.merge(tracks[['Event_ID','track','pre_vv_db','pre_vh_db',
                                    'post_vv_db','post_vh_db','shift','strong']],
                             on=['Event_ID','track'], validate='many_to_one')
    dv = obs.post_vv_db-obs.pre_vv_db
    dh = obs.post_vh_db-obs.pre_vh_db
    obs['progress'] = ((obs.vv_db_median-obs.pre_vv_db)*dv +
                       (obs.vh_db_median-obs.pre_vh_db)*dh) / obs['shift'].pow(2)
    obs['s1_date'] = pd.to_datetime(obs.s1_date)
    output = []
    for e in manifest.itertuples():
        start, end = pd.Timestamp(e.LastPre), pd.Timestamp(e.FirstPost)
        tr = tracks[tracks.Event_ID.eq(e.Event_ID) & tracks.eligible]
        samples = obs[obs.Event_ID.eq(e.Event_ID) & obs.strong]
        samples = samples[samples.s1_date.gt(start) & samples.s1_date.lt(end)]
        pre = samples.loc[samples.progress.le(.35), 's1_date'].max()
        post = samples.loc[samples.progress.ge(.65), 's1_date'].min()
        a = max(start, pre) if pd.notna(pre) else start
        b = min(end, post) if pd.notna(post) else end
        coherent = len(tr)>0 and tr['shift'].median()>=1.5 and tr.strong.mean()>=2/3
        width = (b-a).days
        accepted = coherent and len(tr)>=2 and start.month>=5 and 0<=width<(end-start).days
        output.append([e.Event_ID, str(a.date()), str(b.date()), coherent, accepted,
                       str((a if accepted else start).date()),
                       str((b if accepted else end).date()),
                       width if accepted else (end-start).days])
    return pd.DataFrame(output, columns=['Event_ID','candidate_LastPre','candidate_FirstPost',
        'coherent_S1_change','primary_S1_refinement_accepted','final_LastPre','final_FirstPost','final_window_days'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, default=ROOT/'data')
    ap.add_argument('--output', type=Path, default=ROOT/'results/s1_timing.csv')
    args = ap.parse_args()
    result = refine(pd.read_csv(args.data/'s1_manifest.csv'),
                    pd.read_csv(args.data/'s1_tracks.csv'),
                    pd.read_csv(args.data/'s1_observations.csv'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)
