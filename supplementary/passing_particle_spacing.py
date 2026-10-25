"""Finite spacing checks for free passing E-bar particles; no runtime edits.

The quantitative distance is the phase-normalized trajectory coordinate
x + eta_E(phase)/15, not the phase-dependent left edge of a JSON word.
Only standard-library code is used. An optional database scan looks for a
compact control pair, without claiming reachability or database closure.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import sqlite3
import sys
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from pyca_verifier.automaton import BitRow, step
from pyca_verifier.patterns import ETHER, TABLES, word
from program_joins import COR, component_sources, coordinates


def position(phase, time):
    now = (phase + time) % 30
    numerator = COR['E'][phase] - COR['E'][now] - 4*time
    assert numerator % 15 == 0
    return numerator // 15, now


def guarded_overlap():
    """Exhaust all phase words, including every overlapping occurrence."""
    minima = []
    for p in range(30):
        a = ETHER + word('E', p) + ETHER
        for q in range(30):
            b = ETHER + word('E', q) + ETHER
            for d in range(1, len(a)+1):
                n = min(len(a)-d, len(b))
                if n <= 0 or a[d:d+n] == b[:n]:
                    minima.append((d,p,q))
                    break
    assert min(minima)[0] == 21
    return {'phase_pairs':len(minima), 'minimum_literal_core_start_gap':21,
            'witness':list(min(minima)),
            'scope':'All distinct occurrences of guarded E words in any binary row.'}


def pair_orbits():
    """Enumerate every small ether join; use a symbolic large-gap tail.

    Negative tile numbers are considered only as overlapping canonical cuts,
    with all overlapping bits required to agree. They are not padding used
    by the encoder. Positive normalized separation is required.
    """
    counts = {'incompatible_or_nonpositive':0,'changed':0,
              'core_orbit_only':0,'core_orbit_and_guards':0}
    stable=[]; negative_stable=[]; large_gap=[]
    roles={}; trials=0; nonordered_or_overlapping_candidates=0
    for p in range(30):
        for q in range(30):
            a,b=word('E',p),word('E',q)
            for k in range(-3,4):
                dx=len(a)+14*k
                delta_e=15*dx+COR['E'][q]-COR['E'][p]
                if delta_e <= 0:
                    counts['incompatible_or_nonpositive']+=1
                    continue
                cells=dict(enumerate(a)); compatible=True
                for at, bit in enumerate(b,dx):
                    if at in cells and cells[at]!=bit: compatible=False
                    cells[at]=bit
                if not compatible:
                    counts['incompatible_or_nonpositive']+=1
                    continue
                if k<0 or dx<=0:
                    nonordered_or_overlapping_candidates+=1
                # For k>=0, the omitted cells are the actual aligned ether.
                lo=min(cells); hi=max(cells)+1
                core=''.join(cells.get(at,ETHER[(at-len(a))%14]) for at in range(lo,hi))
                initial=ETHER*8+core+ETHER*8
                row=BitRow.from_word(initial,origin=lo-112)
                exact=True; guarded=True; minimum=dx; min_ether=10**9
                for t in range(31):
                    x,pp=position(p,t); yy,qq=position(q,t); y=dx+yy
                    bits=row.word(); minimum=min(minimum,y-x)
                    min_ether=min(min_ether,y-x-len(word('E',pp)))
                    for z,phase in ((x,pp),(y,qq)):
                        at=z-row.origin; w=word('E',phase)
                        exact &= bits[at:at+len(w)]==w
                        guarded &= bits[at-14:at+len(w)+14]==ETHER+w+ETHER
                    if t==30:
                        at=row.origin+8-(lo-112)
                        exact &= bits==initial[at:at+row.width]
                    else:
                        row=step(row)
                trials+=1
                if not exact:
                    counts['changed']+=1
                    continue
                counts['core_orbit_and_guards' if guarded else 'core_orbit_only']+=1
                r={'left_phase':p,'right_phase':q,'ether_tiles':k,
                   'delta_e':delta_e,'minimum_literal_gap':minimum,
                   'all_phases_guarded':guarded,'minimum_ether_gap':min_ether}
                stable.append(r)
                if k<0:negative_stable.append(r)
                if k==3:large_gap.append(r)
                xa,ua=coordinates((0,p));xb,ub=coordinates((dx,q))
                if (xb-xa-1)%2==0 and (ub-ua-63)%14==0:
                    key=f"over{((xb-xa-1)//2)%4}_up{((ub-ua-63)//14)%6}"
                    roles[key]=min(roles.get(key,10**9),delta_e)
    assert not negative_stable and nonordered_or_overlapping_candidates==0
    assert len(large_gap)==900 and all(r['all_phases_guarded'] and r['minimum_ether_gap']>=14 for r in large_gap)
    low=min(stable,key=lambda r:r['delta_e'])
    assert low['delta_e']==357
    return {'parameter_cases':30*30*7,'native_orbits':trials,'classification':counts,
            'stable_cases':len(stable),'minimum_delta_e':357,
            'minimum_normalized_gap':'357/15 = 119/5 = 23.8 cells',
            'minimum_witness':low,'minimum_by_Cook_residues':roles,
            'negative_overlap_stable_cases':len(negative_stable),
            'overlapping_or_reversed_core_cut_candidates':nonordered_or_overlapping_candidates,
            'large_gap_base_cases':len(large_gap),
            'large_gap_extension':'Every base join with three ether tiles has at least 14 ether cells in all 30 phases. Further ether tiles separate independent radius-one neighborhoods and increase delta_e by 210 per tile.',
            'literal_edge_control':next(r for r in stable if (r['left_phase'],r['right_phase'],r['ether_tiles'])==(0,20,0)),
            'scope':'All phase-compatible isolated pairs whose two prescribed E cores follow their free orbits and whose complete guarded pair translates by -8 after 30 ticks. Reactions need separate bounded collars.'}


def emitted_bits():
    """Check two successive accepted data symbols, not just one packet."""
    B,trials=component_sources()
    def emit(theta,s,first):
        p,g=TABLES['yn'][str(theta)]['0'];f='PC' if first else 'SC';x=14*g
        def at(f,p,x):
            return [(15*x+e,tau) for e,tau in zip(B[f][p]['offsets'],B[f][p]['phases_at_t0'])]
        out=at(f,p,x);x+=len(word(f,p))
        if first:p=(p+14)%30
        q,g=TABLES['yn'][str(p)][s];x+=14*g
        out+=at('SC',q,x);x+=len(word('SC',q))
        return x,q,out
    records=[]
    for first in (False,True):
        for p in range(30):
            for s in 'YN':
                w,q,a=emit(p,s,first)
                for ss in 'YN':
                    _,_,b=emit(q,ss,False)
                    outputs=a+[(e+15*w,tau) for e,tau in b]
                    within=seam=10**9
                    for t in range(30):
                        xs=[]
                        for e,tau in outputs:
                            phase=(t+tau)%30;v=e-4*t-COR['E'][phase]
                            assert v%15==0
                            xs.append(v//15)
                        gaps=[y-x for x,y in zip(xs,xs[1:])]
                        within=min(within,*gaps[:3],*gaps[4:]);seam=min(seam,gaps[3])
                    records.append({'first_principal':first,'phase':p,'symbols':s+ss,
                                    'within_packet_minimum':within,'between_packet_minimum':seam})
    assert len(records)==240
    assert min(r['within_packet_minimum'] for r in records)==105
    assert {r['between_packet_minimum'] for r in records}=={161}
    return {'native_component_trials':trials,'adjacent_symbol_cases':len(records),
            'temporal_phases_per_case':30,'within_packet_minimum_literal_gap':105,
            'between_packet_minimum_literal_gap':161,
            'scope':'Successive accepted data letters through actual PC/SC tables, before subsequent scattering. Empty/leader seams are not included.'}


def control_scan(database):
    """Look for all phases of the compact control; absence is only empirical."""
    row=BitRow.from_word(ETHER*20+word('E',0)+word('E',20)+ETHER*20,origin=-280)
    patterns=[]
    for t in range(30):
        x,p=position(0,t); y,q=position(20,t);y+=len(word('E',0))
        end=max(x+len(word('E',p)),y+len(word('E',q)))
        patterns.append(row.word()[x-row.origin-14:end-row.origin+14]);row=step(row)
    regex=re.compile('|'.join(sorted(set(patterns),key=len,reverse=True)))
    uri=Path(database).resolve().as_uri()+'?mode=ro'
    hits=[];count=0
    with sqlite3.connect(uri,uri=True) as db:
        for pid,width,packed in db.execute('select id,cells,packed_zlib from patterns'):
            bits=format(int.from_bytes(zlib.decompress(packed),'little'),f'0{width}b')[::-1]
            match=regex.search(bits);count+=1
            if match:hits.append({'pattern_id':pid,'offset':match.start()})
    return {'database_sha256':sha256(Path(database).read_bytes()).hexdigest(),
            'distinct_words_scanned':count,'control_phase_words':len(set(patterns)),
            'matched_words':len(hits),'first_hits':hits[:20],
            'scope':'This isolated close-pair control was searched; this is not a general particle classifier or reachability proof.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path)
    parser.add_argument('--output',type=Path,default=HERE/'passing-particle-spacing.json')
    args=parser.parse_args()
    if not __debug__:raise SystemExit('Run without -O; assertions are verification checks.')
    result={'guarded_word_density':guarded_overlap(),'free_pair_spacing':pair_orbits(),
            'actual_adjacent_accepted_symbols':emitted_bits(),
            'normalization':'e=15*x+4*t+eta_E(p); free spatial reference b(t)=(e-4*t)/15',
            'global_CA_decomposition_proved':False,
            'conditional_density_statement':'If all pending passers outside a fixed boundary collar belong to the compatible free E stream, their normalized anchors are separated by at least 119/5, hence by 14. Thus their count in an interval of length G is at most floor(G/14)+1. Non-free passers must be bounded separately.'}
    if args.database:result['compact_control_database_scan']=control_scan(args.database)
    paths=[Path(__file__),HERE/'program_joins.py',ROOT/'pyca_verifier/patterns.py',
           ROOT/'pyca_verifier/automaton.py',ROOT/'pyca_verifier/data/gliders.json',
           *sorted((ROOT/'pyca_verifier/data').glob('dict_*.json'))]
    result['source_sha256']={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in paths}
    result['finite_checks_passed']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('finite_checks_passed','normalization','global_CA_decomposition_proved')},indent=2))
    print(args.output)

if __name__=='__main__':main()
