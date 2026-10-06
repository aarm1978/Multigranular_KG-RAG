"""Exact-first mechanical boundary sensitivity; no semantic equivalence judgments."""

from fractions import Fraction

from . import scierc_external_anchor as a


def iou(left: tuple, right: tuple) -> Fraction:
    """Return exact inclusive-token intersection over union."""
    intersection = max(0, min(left[1], right[1])-max(left[0], right[0])+1)
    return Fraction(intersection, left[1]-left[0]+right[1]-right[0]+2-intersection)


def signature(item: dict, layer: str):
    """Use the unchanged strict scorer's signature universe."""
    spans = [tuple(span) for span in item["spans"]]
    return (*spans[0], item["label"]) if layer == "entity" else a.relation_signature(item["label"], *spans)


def orientations(prediction: dict, gold: dict, layer: str) -> list:
    """List eligible same-sentence orientations; never constrain endpoint types."""
    if prediction["documentID"] != gold["documentID"] or prediction["label"] != gold["label"]:
        return []
    sentences = prediction["sentenceIndices"] + gold["sentenceIndices"]
    if len(set(sentences)) != 1:
        return []
    choices = [("direct",gold["spans"])]
    if layer == "relation" and prediction["label"] in a.SYMMETRIC_RELATIONS:
        choices.append(("swapped",list(reversed(gold["spans"]))))
    result=[]
    for name,spans in choices:
        weights=[iou(tuple(p),tuple(g)) for p,g in zip(prediction["spans"],spans)]
        if all(weights): result.append((name,sum(weights,Fraction())/len(weights)))
    return sorted(result,key=lambda row:(-row[1], row[0]))


def maximum_matching(edges: dict) -> list:
    """Min-cost max-flow: cardinality, rational IoU, then lexical pair-set order.

    Successive Bellman-Ford augmentations retain exact (Fraction, integer) costs.
    The secondary binary objective uniquely orders equal-cardinality edge sets.
    No float epsilon, greedy conflict resolution, or external solver is used.
    """
    pairs=sorted(edges)
    if not pairs: return []
    left=sorted({p for p,g in pairs}); right=sorted({g for p,g in pairs})
    nodes=[("source","")]+[("p",x) for x in left]+[("g",x) for x in right]+[("sink","")]
    graph={node:[] for node in nodes}; refs={}
    def add(u,v,cost):
        """Add a unit-capacity edge and its cost-negated reverse."""
        forward=[v,len(graph[v]),1,cost]; reverse=[u,len(graph[u]),0,(-cost[0],-cost[1])]
        graph[u].append(forward); graph[v].append(reverse)
        return forward
    zero=(Fraction(),0); source=nodes[0]; sink=nodes[-1]
    for p in left: add(source,("p",p),zero)
    for rank,pair in enumerate(pairs):
        refs[pair]=add(("p",pair[0]),("g",pair[1]),(-edges[pair],-(1 << (len(pairs)-rank-1))))
    for g in right: add(("g",g),sink,zero)
    while True:
        distances={source:zero}; previous={}
        for _ in range(len(nodes)-1):
            changed=False
            for u in nodes:
                if u not in distances: continue
                for index,edge in enumerate(graph[u]):
                    v,reverse,capacity,cost=edge
                    if not capacity: continue
                    candidate=(distances[u][0]+cost[0],distances[u][1]+cost[1])
                    if v not in distances or candidate < distances[v]:
                        distances[v]=candidate; previous[v]=(u,index); changed=True
            if not changed: break
        if sink not in distances: break
        node=sink
        while node!=source:
            u,index=previous[node]; edge=graph[u][index]
            edge[2]-=1; graph[node][edge[1]][2]+=1; node=u
    return [pair for pair in pairs if refs[pair][2]==0]


def match_layer(predictions: list, gold: list, layer: str) -> dict:
    """Lock exact matches first, then optimize only eligible residual pairs."""
    ps={item["id"]:item for item in predictions}; gs={item["id"]:item for item in gold}
    assert len(ps)==len(predictions) and len(gs)==len(gold)
    pkeys={(item["documentID"],signature(item,layer)):item["id"] for item in predictions}
    gkeys={(item["documentID"],signature(item,layer)):item["id"] for item in gold}
    assert len(pkeys)==len(ps) and len(gkeys)==len(gs)
    locked=sorted((pkeys[key],gkeys[key]) for key in pkeys.keys() & gkeys.keys())
    locked_p={p for p,g in locked}; locked_g={g for p,g in locked}
    eligible={}; orientation_records={}
    for p in sorted(ps.keys()-locked_p):
        for g in sorted(gs.keys()-locked_g):
            options=orientations(ps[p],gs[g],layer)
            if options:
                eligible[p,g]=options[0][1]; orientation_records[p,g]=options
    selected=maximum_matching(eligible)
    used_p=locked_p | {p for p,g in selected}; used_g=locked_g | {g for p,g in selected}
    return {"locked":locked,"selected":selected,"eligible":eligible,"orientations":orientation_records,
            "unmatchedPredictions":sorted(ps.keys()-used_p),"unmatchedGold":sorted(gs.keys()-used_g)}


def discrepancy_flags(prediction: dict, gold: dict, layer: str) -> list:
    """Return overlapping diagnostic flags, not mutually exclusive errors."""
    if prediction["documentID"] != gold["documentID"]: return []
    p=prediction["spans"]; g=gold["spans"]
    if layer=="entity":
        return ["exact_span_different_type"] if p==g and prediction["label"]!=gold["label"] else []
    direct=p==g; reverse=p==list(reversed(g)); flags=[]
    if (direct or reverse) and prediction["label"]!=gold["label"]: flags.append("exact_endpoints_different_label")
    if reverse and p[0]!=p[1] and (prediction["label"] not in a.SYMMETRIC_RELATIONS or gold["label"] not in a.SYMMETRIC_RELATIONS):
        flags.append("exact_endpoints_direction_reversal")
    return flags
