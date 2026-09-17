"""Build a local, sanitized Annotator-2 reliability bundle."""
from __future__ import annotations
import hashlib, json, shutil, zipfile
from pathlib import Path

IDS = {"pub:34:sec:0015:unit:0001", "pub:79:sec:0004:unit:0001"}
COPY = ("src/annotation/publication_pilot1", "schemas/publication_pilot1_annotation_record.schema.json", "src/ontology/ontology_spec.yaml", "src/ontology/ciroh_ontology.owl", "src/extraction/llm/publications/publication_target_inventory.yaml", "docs/publication_human_core_reliability_annotation_guide_v0.1.5.md", "data/curation/papers/m2/human_core_gold/publication_human_core_reliability_annotation_package_v0.1.5.json", "data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json")
def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def build(root: Path, output: Path)->Path:
    """Materialize only two-paper context, exact endpoint rows, and runtime files."""
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    inv=[json.loads(x) for x in (root/"data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl").read_text().splitlines() if x]
    papers={x["paperID"] for x in inv if x["sourceUnitID"] in IDS}; inv=[x for x in inv if x["paperID"] in papers]
    refs={r for x in inv for r in x.get("deterministicNodeRefs",[])}
    graph=json.loads((root/"data/interim/papers/publication_nodes_edges.json").read_text()); graph["nodes"]=[x for x in graph["nodes"] if x["id"] in refs]
    for item in COPY:
        s=root/item; d=output/item; d.parent.mkdir(parents=True,exist_ok=True)
        if s.is_dir(): shutil.copytree(s,d,ignore=shutil.ignore_patterns("__pycache__"))
        else: shutil.copy2(s,d)
    # Replace the N=5 freeze with a two-unit transport binding; no other sample units ship.
    freeze={"reliabilitySubset":{"sourceUnitIDs":sorted(IDS)}}
    fp=output/"data/bundle/n2_freeze.json"; fp.parent.mkdir(parents=True,exist_ok=True); fp.write_text(json.dumps(freeze,sort_keys=True)+"\n")
    pp=output/"data/curation/papers/m2/human_core_gold/publication_human_core_reliability_annotation_package_v0.1.5.json"
    package=json.loads(pp.read_text()); package["authorities"]["sampleFreeze"]={"path":"data/bundle/n2_freeze.json","sha256":sha(fp)}; pp.write_text(json.dumps(package,indent=2,sort_keys=True)+"\n")
    (output/"data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json").unlink()
    invp=output/"data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"; invp.parent.mkdir(parents=True,exist_ok=True); invp.write_text("\n".join(json.dumps(x,sort_keys=True) for x in inv)+"\n")
    gp=output/"data/interim/papers/publication_nodes_edges.json"; gp.parent.mkdir(parents=True,exist_ok=True); gp.write_text(json.dumps(graph,sort_keys=True)+"\n")
    docs={x["paperID"]:x["canonicalTextSha256"] for x in inv}; mp=output/"data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json"; mp.write_text(json.dumps({"canonicalDocumentHashes":docs,"phaseBArtifactHash":sha(gp)},sort_keys=True)+"\n")
    for source in sorted({x["sourceFile"] for x in inv}):
        d=output/source; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(root/source,d)
    for relative in ("data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl","schemas/publication_pilot1_unit_routing.schema.json"):
        d=output/relative; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(root/relative,d)
    (output/"README_ANNOTATOR.md").write_text("# Annotator 2 Reliability Bundle\n\nUse Python 3.9+ with PyYAML installed. Do not consult external sources or researcher/model annotations.\n\nLaunch:\n```bash\nPYTHONPATH=. python -m src.annotation.publication_pilot1.calibration.app --mode human-core-reliability --annotation-session-id HUMAN_CORE_N2_RELIABILITY_V015 --annotator-id HUMAN_CORE_RELIABILITY_ANNOTATOR_2 --port 8766\n```\nOpen http://127.0.0.1:8766. Pause/resume in the UI. After both submissions, use **Export this session** and return `var/publication_pilot1_annotation/human-core/reliability-annotator-2/exports/HUMAN_CORE_N2_RELIABILITY_V015.annotation.json`.\n")
    paths=["data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl","data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl","schemas/publication_pilot1_unit_routing.schema.json","data/interim/papers/publication_nodes_edges.json"]
    manifest={"bundleVersion":"1.0","runtimeHashPaths":paths,"files":{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/"RELIABILITY_BUNDLE_MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    with zipfile.ZipFile(output.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(output))
    return output
if __name__=='__main__': print(build(Path.cwd(),Path.cwd()/"var/reliability_bundle/HUMAN_CORE_N2_RELIABILITY_V015"))
