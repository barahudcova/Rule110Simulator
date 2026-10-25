"""Native emission calibrations and absolute E-stream seam bounds.

Checks every raw-source phase, ordinary and short reads, S/S-prime seams,
and the actual finite lookup tables. No encoder or decoder is modified.
"""
from pathlib import Path
from hashlib import sha256
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from pyca_verifier.automaton import BitRow,step
from pyca_verifier.patterns import ETHER,TABLES,word
from program_joins import find,evolve,intercept,component_sources,coordinates,explained
from distance_conventions import derive_normalizations


def beam(row):
    """Find the common head phase as a coordinate; retain the whole frontier."""
    for _ in range(30):
        bits=row.word();i=bits.find(ETHER+word('L',2)[:99])
        if i>=0:
            end=bits.rfind(ETHER)
            while end>=14 and bits.startswith(ETHER,end-14):end-=14
            return bits[i+14:end],row.origin+i+14,row.time
        row=step(row)
    raise AssertionError('Prepared head phase not found')


def calibrate(B):
    ap,ag=B['SC'][0]['witnesses'][0];q,g=TABLES['sc_sl']['0']
    bits=ETHER*300+word('acceptor',ap)+ETHER*ag+word('SC',0)+ETHER*(8+g)+word('SL',q)+ETHER*300
    short,_,_=beam(evolve(BitRow.from_word(bits,origin=-4200),2400))
    assert len(short)==216
    norm=derive_normalizations();consumptions=[];garbage={};gamma={};preparations=[]
    for name,leader in [('L',word('L',2)),('short',short)]:
        garbage[name]={}
        for s in 'YN':
            values=set()
            for p in range(7):
                for gap in range(20,24):
                    lx=len(word(s,p))+14*gap
                    row=BitRow.from_word(ETHER*500+word(s,p)+ETHER*gap+leader+ETHER*500,origin=-7000)
                    cs=find(row,'C2');c=cs[-1][0]+norm['C2'][str(cs[-1][1])]
                    X,_=coordinates(find(row,'E')[0]);assert (X-c+3)%2==0
                    if ((X-c+3)//2)%4!=1:continue
                    row=evolve(row,3000)
                    found={f:find(row,f) for f in ('E','C2','acceptor','rejector')}
                    want='acceptor' if name=='L' and s=='Y' else 'rejector'
                    other='rejector' if want=='acceptor' else 'acceptor'
                    assert len(found['E'])==2 and len(found[want])==1 and not found[other] and not found['C2']
                    assert explained(row,found)
                    offsets=tuple(intercept('E',h,row.time)-15*lx for h in found['E'])
                    values.add(offsets)
                    consumptions.append(dict(leader=name,consumed=s,static_phase=p,ether_tiles=gap,offsets=offsets))
            assert len(values)==1
            garbage[name][s]=next(iter(values))
    assert garbage=={'L':{'Y':(-446,4587),'N':(-446,1395)},'short':{'Y':(-446,1731),'N':(-446,1731)}}
    for control in ('acceptor','rejector'):
        for p in range(30):
            if control=='acceptor':ap,ag=B['SC'][p]['witnesses'][0]
            else:
                valid=[]
                for rp in range(3):
                    for gap in (4,5):
                        row=evolve(BitRow.from_word(ETHER*160+word(control,rp)+ETHER*gap+word('SC',p)+ETHER*160),1200)
                        found={f:find(row,f) for f in ('E','acceptor','rejector')}
                        if len(found['rejector'])==1 and not found['E'] and not found['acceptor'] and explained(row,found):valid.append((rp,gap))
                assert valid;ap,ag=valid[0]
            for table,fam in [('rl','RL'),('sc_sl','SL')]:
                for marker in ((0,4) if fam=='RL' else (0,)):
                    q,g=TABLES[table][str(p)]
                    rx=len(word(control,ap))+14*ag+len(word('SC',p))+14*(8+g+marker)
                    bits=ETHER*300+word(control,ap)+ETHER*ag+word('SC',p)+ETHER*(8+g+marker)+word(fam,q)+ETHER*300
                    actual,lx,t=beam(evolve(BitRow.from_word(bits,origin=-4200),2400))
                    assert actual==(word('L',2) if fam=='RL' else short)
                    value=15*(lx-rx)+4*t
                    gamma.setdefault(fam,{}).setdefault(q,set()).add(value)
                    preparations.append(dict(incoming=control,previous_SC_phase=p,raw_family=fam,raw_phase=q,marker=marker,gamma=value))
    assert all(len(v)==1 for phases in gamma.values() for v in phases.values())
    gamma={f:{p:next(iter(v)) for p,v in phases.items()} for f,phases in gamma.items()}
    assert len(gamma['RL'])==len(gamma['SL'])==30 and gamma['RL']==gamma['SL']
    short_witness={};direct_short=[];successors=[]
    for p in range(30):
        for rp in range(3):
            for gap in (4,5):
                sx=len(word('rejector',rp))+14*gap
                prefix=ETHER*300+word('rejector',rp)+ETHER*gap+word('SL',p)
                try:actual,lx,t=beam(evolve(BitRow.from_word(prefix+ETHER*300,origin=-4200),1200))
                except AssertionError:continue
                if actual==short:
                    value=15*(lx-sx)+4*t
                    assert value==gamma['SL'][p]
                    short_witness.setdefault(p,(rp,gap))
                    direct_short.append(dict(raw_phase=p,rejector_phase=rp,ether_tiles=gap,gamma=value))
        assert p in short_witness
    for p,(rp,gap) in short_witness.items():
        sx=len(word('rejector',rp))+14*gap
        prefix=ETHER*300+word('rejector',rp)+ETHER*gap+word('SL',p)
        for table,fam in [('sl_rl','RL'),('sl_sl','SL')]:
            for marker in ((0,4) if fam=='RL' else (0,)):
                q,g=TABLES[table][str(p)];rx=sx+len(word('SL',p))+14*(g+marker)
                full=prefix+ETHER*(g+marker)+word(fam,q)+ETHER*300
                frontier,x1,t1=beam(evolve(BitRow.from_word(full,origin=-4200),1200))
                for s,sp in [('Y',0),('N',4)]:
                    shift=len(word(s,sp))+28
                    test=BitRow.from_word(ETHER*300+word(s,sp)+ETHER*2+frontier+ETHER*300,origin=-4200-shift)
                    after=evolve(test,2400)
                    actual,x2,t2=beam(after)
                    at_head=evolve(after,t2-after.time)
                    outgoing=[h for h in find(at_head,'E') if h[0]<x2-14]
                    garbage_e=tuple(intercept('E',h,t2) for h in outgoing)
                    assert garbage_e==garbage['short'][s], (p,table,marker,s,garbage_e)
                    assert actual==(word('L',2) if fam=='RL' else short)
                    value=15*(x1+x2-rx)+4*(t1+t2)
                    assert value==gamma[fam][q]
                    successors.append(dict(previous_raw_short_phase=p,table=table,marker=marker,consumed=s,next_raw_phase=q,gamma=value,outgoing_garbage_e=garbage_e))
    return short,garbage,gamma,dict(
        garbage_read_cases=consumptions,raw_preparation_cases=preparations,
        direct_short_preparation_cases=direct_short,short_successor_cases=successors)


def source_bounds(B,garbage,gamma):
    seams=[]
    for p in range(30):
        theta=(p+22)%30;cp,g=TABLES['yn'][str(theta)]['0']
        first=15*(len(word('RL',p))+14*g)+B['PC'][cp]['offsets'][0]
        seams.append(dict(kind='GD',phase=p,delta_e=first-gamma['RL'][p]-garbage['L']['Y'][-1]))
        for tab,f in [('rl','RL'),('sc_sl','SL')]:
            q,g=TABLES[tab][str(p)]
            first=15*(len(word('SC',p))+14*(8+g))+gamma[f][q]+garbage['L' if f=='RL' else 'short']['Y'][0]
            seams.append(dict(kind='DG',phase=p,table=tab,delta_e=first-B['SC'][p]['offsets'][-1]))
        for tab,f in [('sl_rl','RL'),('sl_sl','SL')]:
            q,g=TABLES[tab][str(p)]
            first=15*(len(word('SL',p))+14*g)+gamma[f][q]-446
            seams.append(dict(kind='GG_empty',phase=p,table=tab,delta_e=first-gamma['SL'][p]-1731))
    cp,g=TABLES['yn']['20']['0']
    initial_gd=15*(len(word('L',2))+14*g)+B['PC'][cp]['offsets'][0]-4587
    assert initial_gd==2541
    # Any rejected nonempty appendant contains >=12 components. All actual
    # ether-table gaps are nonnegative, and the trailing padding has112cells.
    minimum_widths={f:min(len(word(f,p)) for p in range(30)) for f in ('RL','PC','SC')}
    assert all(g>=0 for tab in ('rl','sc_sl','sl_rl','sl_sl') for _,g in TABLES[tab].values())
    assert all(g>=0 for values in TABLES['yn'].values() for _,g in values.values())
    rejected=15*(minimum_widths['RL']+minimum_widths['PC']+11*minimum_widths['SC']+112)+min(gamma['RL'].values())-max(gamma['RL'].values())-1841
    initial_rejected=15*(len(word('L',2))+minimum_widths['PC']+11*minimum_widths['SC']+112)+min(gamma['RL'].values())-1841
    # DD: derive every two-letter output and compare every neighboring e.
    def emit(theta,s,first):
        p,g=TABLES['yn'][str(theta)]['0'];family='PC' if first else 'SC';x=14*g
        es=[15*x+e for e in B[family][p]['offsets']];x+=len(word(family,p))
        if first:p=(p+14)%30
        q,g=TABLES['yn'][str(p)][s];x+=14*g
        es += [15*x+e for e in B['SC'][q]['offsets']];x+=len(word('SC',q))
        return x,q,es
    dd=[]
    for first in (False,True):
        for p in range(30):
            for s in 'YN':
                width,q,a=emit(p,s,first)
                for ss in 'YN':
                    _,_,b=emit(q,ss,False);es=a+[e+15*width for e in b]
                    dd.append(min(y-x for x,y in zip(es,es[1:])))
    bounds={k:min(s['delta_e'] for s in seams if s['kind']==k) for k in ('GD','DG','GG_empty')}
    bounds.update(DD=min(dd),GG_within=min(v[1]-v[0] for variants in garbage.values() for v in variants.values()),GG_rejected_nonempty_lower_bound=rejected,initial_GD=initial_gd,initial_GG_rejected_nonempty_lower_bound=initial_rejected)
    assert min(bounds.values())==1325 and min(dd)==1757
    return {'seams':seams,'lower_bounds_e':bounds,'minimum_component_widths':minimum_widths,
            'DD_two_letter_cases':len(dd),'minimum_source_e_difference':min(bounds.values())}


def main():
    if not __debug__:raise SystemExit('Run without -O.')
    B,trials=component_sources()
    short,garbage,gamma,native=calibrate(B)
    bounds=source_bounds(B,garbage,gamma)
    sources=[Path(__file__),HERE/'program_joins.py',HERE/'distance_conventions.py',ROOT/'pyca_verifier/encoder.py',ROOT/'pyca_verifier/patterns.py',ROOT/'pyca_verifier/automaton.py',ROOT/'pyca_verifier/data/gliders.json',*sorted((ROOT/'pyca_verifier/data').glob('dict_*.json'))]
    result=dict(passed=True,minimum_source_e_difference=bounds['minimum_source_e_difference'],
        component_native_trials=trials,garbage_offsets_relative_L2=garbage,
        raw_to_prepared_source_gamma=gamma,native=native,bounds=bounds,
        incoming_difference_formula='delta_e_at_fixed_surviving_C2 = delta_e_source + 684*d; d>=0 intervening completed reads',
        conditional_minimum_incoming_e_difference=1325,
        minimum_ideal_arrival_separation_ticks='(1325-105)/4 = 305',
        scope='Finite native emission calibrations and table inequalities, conditional on the intended ordered crossing/source network. No global CA embedding proof.',
        source_sha256={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sources})
    dest=HERE/'passing-source-seams.json';dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'minimum_source_e_difference':1325,'bounds':bounds['lower_bounds_e'],'read_cases':len(native['garbage_read_cases']),'raw_preparation_cases':len(native['raw_preparation_cases']),'short_successor_cases':len(native['short_successor_cases'])},indent=2));print(dest)

if __name__=='__main__':main()
