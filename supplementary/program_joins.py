"""Finite program grammar, Cook distances and native leader-reaction audit.

Read only this release's binary catalogue, phase tables and component geometry.
Use exact native Rule 110 updates for component emission, leader preparation,
short-leader consumption and the complete successor frontier. No ready-word or
decoder checks are performed. Run with Python 3.10+ and without -O.

run() returns a report and writes results/program-joins.json. Any failed
condition produces a nonzero exit status when invoked as a script. The output
retains witnesses and exact endpoint checks, not only aggregate counts.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))
from pyca_verifier.patterns import TABLES, ETHER, word, DATA
from pyca_verifier.automaton import BitRow, step
if __package__:
    from .program_geometry import encoder_program_joins, validate_program_joins, _cycle_offsets
else:
    from program_geometry import encoder_program_joins, validate_program_joins, _cycle_offsets

PERIOD = {'E':30, 'acceptor':3, 'rejector':3}
COEFF = {'E':(15,4), 'acceptor':(3,-2), 'rejector':(3,-2)}
PAT = {f:[ETHER+word(f,p)+ETHER for p in range(n)] for f,n in PERIOD.items()}
PAT['C2'] = [ETHER+word('C2',p)+ETHER for p in range(7)]


def find(row, family):
    bits = row.word()
    result = []
    for p, pat in enumerate(PAT[family]):
        x = bits.find(pat)
        while x >= 0:
            result.append((row.origin+x+14,p))
            x = bits.find(pat,x+1)
    return sorted(result)


def evolve(row,n):
    for _ in range(n):
        row = step(row)
    return row


def corrections(f):
    row = BitRow.from_word(ETHER*30+word(f,0)+ETHER*30,origin=-420)
    s,c = COEFF[f]
    result = {}
    for t in range(PERIOD[f]):
        hits=find(row,f)
        assert len(hits)==1
        x,p=hits[0]
        result[p]=-s*x-c*t
        row=step(row)
    return result

COR={f:corrections(f) for f in PERIOD}


def intercept(f,h,t=0):
    x,p=h
    s,c=COEFF[f]
    return s*x+c*t+COR[f][p]


def explained(row, found):
    bits=row.word()
    rotations={ETHER[i:]+ETHER[:i] for i in range(14)}
    ranges=[(x-row.origin-14,x-row.origin+len(word(f,p))+14)
            for f,hh in found.items() for x,p in hh]
    return all(bits[i:i+14] in rotations or any(a<=i and i+14<=b for a,b in ranges)
               for i in range(len(bits)-13))


def coordinates(h,t=0):
    e=intercept('E',h,t)
    tau=(h[1]-t)%30
    assert (e+4*tau)%15==0 and (e+14*tau)%5==0
    return (e+4*tau)//15,(e+14*tau)//5


def boundary_measurements():
    records=[]
    for name,f,p,g,q,k in encoder_program_joins():
        if g!='SC' and g!='PC':
            continue  # Raw leaders start with En; see native preparation below.
        row=BitRow.from_word(ETHER+word(f,p)+ETHER*k+word(g,q)+ETHER,origin=-14)
        right_x=len(word(f,p))+14*k
        # Track the SAME endpoint particle from phase zero. Canonical cuts
        # sometimes clip its core; a nearest full-word search would silently
        # select the second particle in those phases.
        def endpoint(family, phase, which):
            reference=BitRow.from_word(ETHER+word(family,0)+ETHER,origin=-14)
            h=find(reference,'E')[0 if which=='first' else -1]
            ex,ep=h
            off=lambda q: (-COR['E'][q]-4*q)//15
            turns,q=divmod(ep+phase,30)
            x=ex-off(ep)+off(q)-8*turns-_cycle_offsets(family)[phase]
            return x,q
        a=endpoint(f,p,'last')
        bx,bp=endpoint(g,q,'first')
        b=(right_x+bx,bp)
        for x,ep in (a,b):
            at=x-row.origin
            assert row.word()[at:at+len(word('E',ep))]==word('E',ep),(name,p,'particle core mismatch',x,ep)
        xa,ua=coordinates(a)
        xb,ub=coordinates(b)
        assert (xb-xa-1)%2==0 and (ub-ua-63)%14==0
        over=((xb-xa-1)//2)%4
        up=((ub-ua-63)//14)%6
        records.append(dict(join=name,left=[f,p],right=[g,q],ether_tiles=k,
            last_E=list(a),first_E=list(b),delta_X=xb-xa,delta_U=ub-ua,
            cook_over=over,cook_up=up,passed=(over==0 and up==2)))
    return records


def component_sources():
    """Recompute source intercepts AND full temporal phase from native inputs."""
    out={};trials=0
    for f in ('PC','SC'):
        out[f]={}
        for p in range(30):
            variants=set();witnesses=[]
            for ap in range(3):
                for gap in (4,5):
                    ax=2240;cx=ax+len(word('acceptor',ap))+14*gap
                    row=BitRow.from_word(ETHER*160+word('acceptor',ap)+ETHER*gap+word(f,p)+ETHER*160)
                    row=evolve(row,1200);trials+=1
                    found={fam:find(row,fam) for fam in PERIOD}
                    es=found['E'];aa=found['acceptor']
                    if len(es)==2 and len(aa)==1 and not found['rejector'] and es[-1][0]<aa[0][0] and explained(row,found):
                        offsets=tuple(intercept('E',h,1200)-15*cx for h in es)
                        phases=tuple((h[1]-1200)%30 for h in es)
                        variants.add((offsets,phases));witnesses.append([ap,gap])
            assert len(variants)==1,(f,p,variants)
            offsets,phases=variants.pop()
            out[f][p]=dict(offsets=offsets,phases_at_t0=phases,witnesses=witnesses)
    return out,trials


def grammar():
    states={('first',20,0)};todo=list(states);edges=[];closing=[]
    while todo:
        kind,p,k=todo.pop();targets=[]
        if kind!='empty':
            for s in 'YN':
                q,g=TABLES['yn'][str(p)]['0']
                if kind=='first': q=(q+14)%30
                q,g=TABLES['yn'][str(q)][s]
                targets.append((s,('regular',q,(k+1)%6)))
            if kind=='regular' and k==0:
                for tab in ('rl','sc_sl'):
                    q,g=TABLES[tab][str(p)]
                    targets.append((tab,('first',(q+22)%30,0) if tab=='rl' else ('empty',q,0)))
                    closing.append((kind,p,k,tab))
        else:
            for tab in ('sl_rl','sl_sl'):
                q,g=TABLES[tab][str(p)]
                targets.append((tab,('first',(q+22)%30,0) if tab=='sl_rl' else ('empty',q,0)))
                closing.append((kind,p,k,tab))
        for label,target in targets:
            edges.append((kind,p,k,label,target))
            if target not in states:
                states.add(target);todo.append(target)
    return sorted(states),sorted(closing),edges


def source_closure(B,states):
    result={}
    for coordinate,modulus,scale,advance,within in [
            ('e',84,15,58,[0,77,70,63]),
            ('K',120,15,30,[0,105,90,75]),
            ('U',84,3,34,[0,35,70,21])]:
        def bit(theta,s,first):
            p,g=TABLES['yn'][str(theta)]['0'];f='PC' if first else 'SC';x=14*g
            def vals(f,p,x):
                v=B[f][p];out=[]
                for e,tau in zip(v['offsets'],v['phases_at_t0']):
                    z=e if coordinate=='e' else (e+4*tau if coordinate=='K' else (e+14*tau)//5)
                    out.append(scale*x+z)
                return out
            es=vals(f,p,x);x+=len(word(f,p))
            if first:p=(p+14)%30
            q,g=TABLES['yn'][str(p)][s];x+=14*g
            es+=vals('SC',q,x);x+=len(word('SC',q))
            return x,q,es
        reg={p:bit(p,'Y',False)[2][0] for p in range(30)}
        first={p:bit(p,'Y',True)[2][0] for p in range(30)}
        rl={p:(scale*len(word('RL',p))+first[(p+22)%30])%modulus for p in range(30)}
        sl={}
        for p in range(30):
            q,g=TABLES['sl_rl'][str(p)]
            sl[p]=(scale*(len(word('SL',p))+14*g)+rl[q]-advance)%modulus
        found_bits=set();increments=set();closures={}
        for first_bit in (False,True):
            for p in range(30):
                for s in 'YN':
                    w,q,es=bit(p,s,first_bit)
                    found_bits.add(tuple((e-es[0])%modulus for e in es))
                    increments.add((scale*w+reg[q]-es[0])%modulus)
        for kind,p,k in states:
            tables=('rl','sc_sl') if kind=='regular' and k==0 else ('sl_rl','sl_sl') if kind=='empty' else ()
            for tab in tables:
                q,g=TABLES[tab][str(p)]
                new=(rl if tab in ('rl','sl_rl') else sl)[q]
                old=reg[p] if kind=='regular' else sl[p]
                width=112 if kind=='regular' else len(word('SL',p))
                for marker in ((0,4) if tab in ('rl','sl_rl') else (0,)):
                    residue=(scale*(width+14*(g+marker))+new-old)%modulus
                    closures.setdefault(tab+('_marker4' if marker else ''),set()).add(residue)
        expect_increment=60 if coordinate=='K' else 56
        result[coordinate]=dict(modulus=modulus,within_bit=sorted(found_bits),
            between_bit=sorted(increments),leader_advance={k:sorted(v) for k,v in closures.items()},
            passed=(found_bits=={tuple(within)} and increments=={expect_increment} and all(v=={advance} for v in closures.values())),
            note='SL source label is a virtual continuation through sl_rl; leader preparation is a separate native check.')
    return result



def native_leaders(B, states):
    """Check actual preparation channels, including the S/S-prime transitions.

    Comparing full normalized packet words uses the common L head only to
    choose a coordinate origin; it does not evaluate the ready language.
    """
    def evolve_bits(bits,n):
        return evolve(BitRow.from_word(bits),n)
    def tail_cut(text):
        end=text.rfind(ETHER)
        while end>=14 and text.startswith(ETHER,end-14):end-=14
        return end
    def beam(row):
        for dt in range(30):
            text=row.word();start=text.find(ETHER+word('L',2)[:99])
            if start>=0:
                return text[start+14:tail_cut(text)],row,dt,start+14
            row=step(row)
        return None,row,None,None
    canonical_long,_,_,_=beam(BitRow.from_word(ETHER*100+word('L',2)+ETHER*100))
    assert canonical_long
    ap,ag=B['SC'][0]['witnesses'][0]
    q,g=TABLES['sc_sl']['0']
    prefix=ETHER*300+word('acceptor',ap)+ETHER*ag+word('SC',0)+ETHER*(8+g)+word('SL',q)
    canonical_short,_,_,_=beam(evolve_bits(prefix+ETHER*300,2400))
    assert canonical_short and len(canonical_short)==216
    rejected={}
    for p in range(30):
        valid=[]
        for rp in range(3):
            for gap in (4,5):
                row=evolve_bits(ETHER*160+word('rejector',rp)+ETHER*gap+word('SC',p)+ETHER*160,1200)
                hits={f:find(row,f) for f in PERIOD}
                if len(hits['rejector'])==1 and not hits['E'] and not hits['acceptor'] and explained(row,hits):
                    valid.append([rp,gap])
        assert valid,(p,'no rejector witness')
        rejected[p]=valid
    direct=[]
    for incoming in ('acceptor','rejector'):
        for p in range(30):
            ap,ag=(B['SC'][p]['witnesses'] if incoming=='acceptor' else rejected[p])[0]
            for table,family,target in [('rl','RL',canonical_long),('sc_sl','SL',canonical_short)]:
                for marker in ((0,4) if table=='rl' else (0,)):
                    q,g=TABLES[table][str(p)]
                    bits=ETHER*300+word(incoming,ap)+ETHER*ag+word('SC',p)+ETHER*(8+g+marker)+word(family,q)+ETHER*300
                    actual,row,dt,start=beam(evolve_bits(bits,2400))
                    es=[h for h in find(row,'E') if start is not None and h[0]<row.origin+start-14]
                    ranges=[] if start is None else [(start-14,start+len(actual)+14)]
                    ranges.extend((x-row.origin-14,x-row.origin+len(word('E',ep))+14) for x,ep in es)
                    rotations={ETHER[i:]+ETHER[:i] for i in range(14)};text=row.word()
                    clear=all(text[i:i+14] in rotations or any(a<=i and i+14<=b for a,b in ranges) for i in range(len(text)-13))
                    passed=actual==target and len(es)==(2 if incoming=='acceptor' else 0) and clear
                    direct.append(dict(incoming=incoming,input_phase=p,table=table,marker_tiles=marker,
                        target_phase=q,canonical_target=actual==target,nonether_fully_explained=clear,
                        emitted_E_count=len(es),passed=passed))
    short_phases=sorted({p for kind,p,k in states if kind=='empty'})
    witnesses={}
    for p in short_phases:
        witnesses[p]=[]
        for rp in range(3):
            for gap in (4,5):
                prefix=ETHER*300+word('rejector',rp)+ETHER*gap+word('SL',p)
                actual,row,_,_=beam(evolve_bits(prefix+ETHER*300,1200))
                if actual==canonical_short:
                    witnesses[p].append(dict(phase=rp,gap=gap,ticks=row.time))
        assert witnesses[p],(p,'no short-leader preparation witness')
    def raw_prefix(p):
        w=witnesses[p][0]
        return ETHER*300+word('rejector',w['phase'])+ETHER*w['gap']+word('SL',p)
    def tail(p,table,marker=0):
        q,g=TABLES[table][str(p)]
        return ETHER*(g+marker)+word('SL' if table=='sl_sl' else 'RL',q)
    def consumed_endpoint(row, start, retained):
        """Account for the complete endpoint, including everything left of beam."""
        if start is None or retained is None:
            return dict(passed=False, failure_reasons=['missing retained beam'])
        es=[h for h in find(row,'E') if h[0]<row.origin+start-14]
        residual={f:find(row,f) for f in ('C2','acceptor','rejector')}
        ranges=[(start-14,start+len(retained)+14)]
        ranges.extend((x-row.origin-14,x-row.origin+len(word('E',p))+14) for x,p in es)
        rotations={ETHER[i:]+ETHER[:i] for i in range(14)};text=row.word()
        unexplained=[i for i in range(len(text)-13) if text[i:i+14] not in rotations
                     and not any(a<=i and i+14<=b for a,b in ranges)]
        reasons=[]
        if len(es)!=2: reasons.append('outgoing E count differs from two')
        if any(residual.values()): reasons.append('residual C2 or signal particle')
        if unexplained: reasons.append('nonether window outside accounted particles')
        return dict(passed=not reasons,failure_reasons=reasons,
                    outgoing_garbage_E_particles=es,outgoing_garbage_E_count=len(es),
                    residual_particles=residual,nonether_fully_explained=not unexplained,
                    unexplained_window_count=len(unexplained),unexplained_window_starts=unexplained,
                    native_tick=row.time)
    frontiers=[]
    for p in short_phases:
        q,g=TABLES['sl_sl'][str(p)]
        for table,marker in [('sl_sl',0),('sl_rl',0),('sl_rl',4)]:
            following=tail(q,table,marker)
            expected,_,_,_=beam(evolve_bits(raw_prefix(q)+following+ETHER*300,1200))
            initial,_,_,_=beam(evolve_bits(raw_prefix(p)+tail(p,'sl_sl')+following+ETHER*300,1200))
            for symbol,phase in [('Y',0),('N',4)]:
                actual,row,_,start=beam(evolve_bits(ETHER*300+word(symbol,phase)+ETHER*2+initial+ETHER*300,2400))
                endpoint=consumed_endpoint(row,start,actual)
                frontiers.append(dict(short_phase=p,consumed=symbol,successor_table=table,marker_tiles=marker,
                    endpoint=endpoint,successor_frontier_exact=actual is not None and expected is not None and actual==expected,expected_cells=len(expected) if expected else None))
    seams=[]
    for p in short_phases:
        for table,marker in [('sl_sl',0),('sl_rl',0),('sl_rl',4)]:
            initial,_,_,_=beam(evolve_bits(raw_prefix(p)+tail(p,table,marker)+ETHER*300,1200))
            for symbol,phase in [('Y',0),('N',4)]:
                actual,row,_,start=beam(evolve_bits(ETHER*300+word(symbol,phase)+ETHER*2+initial+ETHER*300,2400))
                endpoint=consumed_endpoint(row,start,actual)
                target=canonical_short if table=='sl_sl' else canonical_long
                seams.append(dict(raw_short_phase=p,consumed=symbol,table=table,marker_tiles=marker,
                    endpoint=endpoint,prepared_successor_exact=actual==target))
    terminal=sorted({p for kind,p,k in states if kind=='regular' and k==0})
    entries=[]
    for incoming in ('acceptor','rejector'):
        for p in terminal:
            ap,ag=(B['SC'][p]['witnesses'] if incoming=='acceptor' else rejected[p])[0]
            q,g=TABLES['sc_sl'][str(p)]
            prefix=ETHER*300+word(incoming,ap)+ETHER*ag+word('SC',p)+ETHER*(8+g)+word('SL',q)
            for table,marker in [('sl_sl',0),('sl_rl',0),('sl_rl',4)]:
                following=tail(q,table,marker)
                actual,_,_,_=beam(evolve_bits(prefix+following+ETHER*300,2400))
                expected,_,_,_=beam(evolve_bits(raw_prefix(q)+following+ETHER*300,1200))
                entries.append(dict(incoming=incoming,terminal_SC_phase=p,raw_short_phase=q,
                    following_table=table,marker_tiles=marker,frontier_exact=actual is not None and expected is not None and actual==expected))
    return dict(short_consumption_seams=seams,short_consumption_cases=len(seams),
        short_consumption_failures=[v for v in seams if not v['prepared_successor_exact'] or not v['endpoint']['passed']],
        component_to_short_successor_frontiers=entries,component_short_frontier_cases=len(entries),
        component_short_frontier_failures=[v for v in entries if not v['frontier_exact']],
        canonical_prepared_short_bits=canonical_short,canonical_prepared_ordinary_bits=canonical_long,
        rejection_witnesses=rejected,component_to_raw_preparation=direct,
        preparation_cases=len(direct),preparation_failures=[v for v in direct if not v['passed']],
        reachable_raw_short_phases=short_phases,short_preparation_witnesses=witnesses,
        short_successor_frontiers=frontiers,short_successor_cases=len(frontiers),
        short_successor_failures=[v for v in frontiers if not v['successor_frontier_exact'] or not v['endpoint']['passed']],
        qualification='Selected isolated acceptor/rejector entries; complete local successor words retained. No global reaction ordering claim.')


def absolute_packets(B):
    by_symbol={s:set() for s in 'YN'}
    for first in (False,True):
        for phase in range(30):
            for symbol in 'YN':
                p,g=TABLES['yn'][str(phase)]['0'];family='PC' if first else 'SC';x=14*g
                es=[15*x+v for v in B[family][p]['offsets']]
                phases=list(B[family][p]['phases_at_t0']);x+=len(word(family,p))
                if first:p=(p+14)%30
                q,g=TABLES['yn'][str(p)][symbol];x+=14*g
                es.extend(15*x+v for v in B['SC'][q]['offsets'])
                phases.extend(B['SC'][q]['phases_at_t0'])
                by_symbol[symbol].add((tuple(v-es[0] for v in es),tuple((v-phases[0])%30 for v in phases)))
    assert by_symbol=={'Y':{((0,1757,4354,6111),(0,7,14,21))},
                       'N':{((0,1757,4690,6447),(0,7,20,27))}}
    return dict(cases=120,packets={s:[dict(relative_e=v[0],relative_native_phase=v[1]) for v in sorted(values)] for s,values in by_symbol.items()},
        N_second_component_e_increase=336,N_second_component_equivalent_translation=[16,24],
        conclusion='N differs from Y by exactly eight A-period vectors on the second component; these output packets are the binary-calibrated moving data.')

def run(output_dir=None):
    if not __debug__:
        raise RuntimeError('Run without -O: native audit assertions must remain enabled.')
    states,closing,edges=grammar()
    measurements=boundary_measurements()
    B,trials=component_sources()
    runtime=json.loads((DATA/'encoder_geometry.json').read_text())
    calibration_equal=all(list(v['offsets'])==runtime['components'][f][str(p)]['offsets']
                          for f,phases in B.items() for p,v in phases.items())
    assert calibration_equal
    source=source_closure(B,states)
    packets=absolute_packets(B)
    free=validate_program_joins(height=70)
    leaders=native_leaders(B,states)
    result=dict(scope='Release program finite grammar and local native particles; no ready/decoder checks',
        source_sha256={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [PROJECT/'pyca_verifier/encoder.py', PROJECT/'pyca_verifier/automaton.py', PROJECT/'pyca_verifier/patterns.py', DATA/'gliders.json', DATA/'encoder_geometry.json', *sorted(DATA.glob('dict_*.json')), Path(__file__), HERE/'program_geometry.py']},
        native_normalizations=COR,component_calibration_matches_runtime=calibration_equal,native_component_source_trials=trials,component_sources=B,
        direct_Cook_component_boundaries=measurements,
        measured_boundary_cases=len(measurements),measured_boundary_failures=[r for r in measurements if not r['passed']],
        native_free_join_check=free,grammar_states=states,grammar_state_count=len(states),
        grammar_closing_transitions=closing,grammar_closing_count=len(closing),grammar_edges=edges,
        full_phase_source_closure=source,absolute_moving_packets=packets,native_leader_joins=leaders,
        global_CA_embedding_proved=False)
    failures=[]
    if result['measured_boundary_failures']:
        failures.append('Cook component boundary distance')
    if free['failures']:
        failures.append('native free packet seam')
    if not all(v['passed'] for v in source.values()):
        failures.append('full-phase source grammar closure')
    failures.extend(k for k,v in leaders.items() if k.endswith('_failures') and v)
    result['failures']=failures
    result['passed']=not failures
    destination=Path(output_dir) if output_dir is not None else HERE/'results'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'program-joins.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    if sys.flags.optimize:
        raise SystemExit('Run without -O: native audit assertions must remain enabled.')
    report=run()
    fields=('passed','failures','measured_boundary_cases','measured_boundary_failures',
            'native_component_source_trials','native_free_join_check','grammar_state_count',
            'grammar_closing_count','full_phase_source_closure')
    print(json.dumps({k:report[k] for k in fields},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
