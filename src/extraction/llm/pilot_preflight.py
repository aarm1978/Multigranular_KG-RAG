"""Offline Step 12C envelope/schema preflight; no transport or credential access."""
from copy import deepcopy
import hashlib
import itertools
import json
from typing import Any


def canonical(value: Any) -> bytes:
    """Serialize exact prospective wire bytes deterministically."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: bytes) -> str:
    """Fingerprint bytes without claiming acquisition verification."""
    return hashlib.sha256(value).hexdigest()


def strict_schema(contract: dict, profile: dict) -> dict:
    """Project structural fields only; optional fields use omission variants.

    Null is not substituted for absent fields because accepted parsers reject it.
    Literal truth, supported targets, gates and dependencies stay downstream.
    """
    string = {"type": "string"}

    def obj(properties):
        """Close each object and require all properties in that variant."""
        return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

    def variants(required, optional):
        """Represent original optional-field semantics without response repair."""
        return {"anyOf": [obj({**required, **{k: optional[k] for k in subset}})
            for size in range(len(optional) + 1) for subset in itertools.combinations(optional, size)]}

    ref = obj({"referenceType": {"type": "string", "enum": contract["referenceTypes"]}, "referenceID": string})
    path_ref = obj({"referenceType": {"type": "string", "enum": ["candidate_edge", "accepted_assertion"]}, "referenceID": string})
    evidence = variants({"sourceUnitID": string, "evidenceText": string},
                        {"locatorAnchor": string, "contribution": string})
    defs = {"reference": ref, "parentReference": path_ref, "fragment": evidence}
    props = {"schemaVersion": {"type": "string", "enum": [contract["schemaVersion"]]}}
    for kind, group, targets in (("node", "candidateNodes", "entities"), ("edge", "candidateEdges", "relations")):
        branches = []
        for identifier in profile[targets]:
            special = contract["specialFields"].get(kind + ":" + identifier, [])
            required_special = contract["requiredSpecialFields"].get(kind + ":" + identifier, [])
            fields = contract["requiredNodeFields" if kind == "node" else "requiredEdgeFields"]
            required = {k: string for k in fields}
            required["inventoryId"] = {"type": "string", "enum": [identifier]}
            required["evidence"] = {"type": "array", "items": {"$ref": "#/$defs/fragment"}}
            if kind == "edge":
                for k in ("source", "target"):
                    required[k] = {"$ref": "#/$defs/reference"}
            optional = {"endpoint": {"$ref": "#/$defs/reference"}} if kind == "node" else {}
            for k in special:
                field = {"type": "array", "items": {"$ref": "#/$defs/parentReference"}} if k == "parentPath" else string
                (required if k in required_special else optional)[k] = field
            # Unclassified/ambiguous purpose proposals may have null category/target.
            # Keep this parser-supported distinction; classification is not a gate.
            if identifier == "C-C07":
                required["categoryKey"] = {"type": ["string", "null"]}
                required["target"] = {"anyOf": [{"$ref": "#/$defs/reference"}, {"type": "null"}]}
            branches.extend(variants(required, optional)["anyOf"])
        props[group] = {"type": "array", "items": {"anyOf": branches}}
    abstention = {k: string for k in contract["abstentionFields"]}
    abstention["sourceUnitIDs"] = {"type": "array", "items": string}
    abstention["disposition"] = {"type": "string", "enum": contract["abstentionDispositions"]}
    props["abstentions"] = {"type": "array", "items": obj(abstention)}
    return {**obj(props), "$defs": defs}


def check_strict_structure(schema: dict) -> None:
    """Check JSON Schema validity and the conservative strict object subset offline.

    This does not certify remote model availability or provider acceptance.
    """
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    if schema.get("type") != "object" or "anyOf" in schema:
        raise ValueError("strict_root_object_required")

    def walk(value):
        """Require closed objects and all declared fields in each variant."""
        if isinstance(value, dict):
            if value.get("type") == "object":
                if value.get("additionalProperties") is not False or set(value.get("required", [])) != set(value.get("properties", {})):
                    raise ValueError("strict_object_fields_invalid")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(schema)


def build_preflight(request_result: dict, *, output_ceiling: int) -> dict:
    """Build a no-tools envelope using only Publication's pure body constructor."""
    from src.extraction.llm.publications.openai_provider import build_responses_api_request
    if request_result.get("status") != "request_ready" or type(output_ceiling) is not int or output_ceiling <= 0:
        raise ValueError("preflight_requires_ready_request_and_positive_ceiling")
    request = deepcopy(request_result["request"])
    semantic_bytes = json.dumps(request, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if digest(semantic_bytes) != request_result["requestSha256"]:
        raise ValueError("semantic_request_digest_mismatch")
    schema = strict_schema(request["responseContract"], request["targetProfile"])
    check_strict_structure(schema)
    input_bytes = canonical(request)
    envelope = build_responses_api_request(input_bytes, model_authorable_schema=schema, max_output_tokens=output_ceiling)
    envelope["text"]["format"]["name"] = request["artifactFamily"] + "_candidate_response"
    if envelope["model"] != "gpt-5.6-sol" or envelope["reasoning"] != {"effort": "medium"} or envelope["store"] is not False or "tools" in envelope:
        raise ValueError("confirmed_provider_configuration_drift")
    wire_bytes = canonical(envelope)
    return {"authorization": "NOT AUTHORIZED", "semanticRequestSha256": digest(semantic_bytes),
            "providerInputSha256": digest(input_bytes), "providerEnvelopeSha256": digest(wire_bytes),
            "schemaSha256": digest(canonical(schema)), "inputBytes": input_bytes, "wireBytes": wire_bytes,
            "semanticRequestBytes": semantic_bytes, "envelope": envelope,
            "inputByteCount": len(input_bytes), "wireByteCount": len(wire_bytes),
            "schemaByteCount": len(canonical(schema)), "outputTokenCeiling": output_ceiling}


def verify_selection(request_result: dict, expected_units: list[dict], expected_owner: str) -> None:
    """Fail on owner, unit order, coordinates or authority drift; never substitute."""
    if request_result.get("status") != "request_ready":
        raise ValueError("source_request_failed")
    body = request_result["request"]
    if body["owner"]["endpointID"] != expected_owner:
        raise ValueError("owner_drift")
    if body["selectedSourceUnitIDs"] != [u["sourceUnitID"] for u in expected_units]:
        raise ValueError("selection_drift")
    if len(body["sourceUnits"]) != len(expected_units):
        raise ValueError("unit_count_drift")
    for actual, expected in zip(body["sourceUnits"], expected_units):
        if any(actual.get(k) != v for k, v in expected.items()):
            raise ValueError("unit_metadata_drift")


# Exact manifest copied from the committed draft at d091d9b; never select by text search.
SELECTIONS = {'HS-01': [{'sourceUnitID': 'hydroshare:7d960b7fdfee480895fd845bade1b75a:abstract:d677e83c412e4859cefff88119b9b914514216a535f465c8acde505db1da7466',
            'startOffsetInAuthority': 0,
            'endOffsetInAuthority': 1056,
            'startLine': 1,
            'endLine': 5,
            'authorityTextSha256': 'aa4a6451568d355df6238376027a7b2bdfc534b8639a4fcb5c35b6c64001f7d1'}],
 'GH-01': [{'sourceUnitID': 'github:unit:b3ffadb0835b7881333ce08fd467f831d22e19c6c733a5666a0853970faacbf7',
            'startOffsetInAuthority': 14,
            'endOffsetInAuthority': 301,
            'startLine': 2,
            'endLine': 2,
            'authorityTextSha256': '0bfb01f0feb2e2592551ccfd8697d563c2158fb849b2a18c13445e9ae55bcf41'}],
 'HUB-01': [{'sourceUnitID': 'hub:unit:e2cca66b5137afd351f37123fc2880e8fb65c5d515459858feb9f79504cadb5b',
             'startOffsetInAuthority': 730,
             'endOffsetInAuthority': 859,
             'startLine': 13,
             'endLine': 13,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:5e8c022b1755675364e554d737c689647fdd27794d32f9caf3377764517db1be',
             'startOffsetInAuthority': 859,
             'endOffsetInAuthority': 961,
             'startLine': 14,
             'endLine': 14,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:f3d3769fc5ca33c66101d20f5057b6ed6b3363cab2cfcb9a1482a0bf7dc9a48f',
             'startOffsetInAuthority': 961,
             'endOffsetInAuthority': 1046,
             'startLine': 15,
             'endLine': 15,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:44553e557599dbf77ebaf0c8bd5ca6bf586800f1d1a8c599a993a4523e2fd933',
             'startOffsetInAuthority': 1046,
             'endOffsetInAuthority': 1185,
             'startLine': 16,
             'endLine': 16,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:553840e51ab1ea38a631bbf81e7d73ee076fb0a0513296107763b6ede841ed77',
             'startOffsetInAuthority': 1185,
             'endOffsetInAuthority': 1405,
             'startLine': 17,
             'endLine': 17,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:be722b4836083d307187dbe80235cdb00369b0c7675c6c2f6dcf6d1a09b67fe1',
             'startOffsetInAuthority': 1424,
             'endOffsetInAuthority': 1591,
             'startLine': 21,
             'endLine': 21,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:c21ba39348438541b64fc2a136f57d5f9921d86d170d41bc01e1b20492f12dc0',
             'startOffsetInAuthority': 1591,
             'endOffsetInAuthority': 1750,
             'startLine': 22,
             'endLine': 22,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:35da192c9972d22d2a2fb31e015f3dcbd660a57eff7454a353712724343eeba6',
             'startOffsetInAuthority': 1750,
             'endOffsetInAuthority': 1909,
             'startLine': 23,
             'endLine': 23,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:6ef237d9ca2a78bdae60ccfa7cdd79b6ce4a129d8c72f49541d9d73567611ebe',
             'startOffsetInAuthority': 1909,
             'endOffsetInAuthority': 2060,
             'startLine': 24,
             'endLine': 24,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:02e6c19d21bff98feec0f813b4fe99ec0544fd3679a931cb150dfc347153d452',
             'startOffsetInAuthority': 2061,
             'endOffsetInAuthority': 2197,
             'startLine': 26,
             'endLine': 26,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:4d5372cf01f66386b7ef5a5c7e375d3edd2393f7eeb3df57b14295816ffbe38a',
             'startOffsetInAuthority': 2197,
             'endOffsetInAuthority': 2361,
             'startLine': 27,
             'endLine': 27,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:f2c7a268009b4702611b1bdeb1229585571e6cc3816dd299c1ef6c6188527421',
             'startOffsetInAuthority': 2361,
             'endOffsetInAuthority': 2458,
             'startLine': 28,
             'endLine': 28,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:96bedc8ad716f67c31dce06e47b35bd8aeecebb07ea2d132e4414fb3e970036a',
             'startOffsetInAuthority': 2458,
             'endOffsetInAuthority': 2582,
             'startLine': 29,
             'endLine': 29,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:7a345074b0c82d7441212ef5315193ea1611314cc82e7d3ec65b9da35e461569',
             'startOffsetInAuthority': 2582,
             'endOffsetInAuthority': 2762,
             'startLine': 30,
             'endLine': 30,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:d821019916b1dd9bf2e62540256d47b4cbfda40e6e664eb592a47aa631c495f7',
             'startOffsetInAuthority': 2763,
             'endOffsetInAuthority': 2891,
             'startLine': 32,
             'endLine': 32,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:d328388712e6ed56ab75e8fdce733c84208feaf388795a489a676bdb1c247655',
             'startOffsetInAuthority': 2891,
             'endOffsetInAuthority': 2964,
             'startLine': 33,
             'endLine': 33,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:88da035041117aed4e5000ec0ac65a4e0876d9f1890b5d70fb8d9753c528d746',
             'startOffsetInAuthority': 2964,
             'endOffsetInAuthority': 3066,
             'startLine': 34,
             'endLine': 34,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:500b172ae5a3f73c4d04969781ff2bdd5daafb34e4d70b48c49f1209b684c495',
             'startOffsetInAuthority': 3066,
             'endOffsetInAuthority': 3127,
             'startLine': 35,
             'endLine': 35,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:6b40a13f6746fc86b72b35c9365d1207feeaf190532f443b8ec626298d4fa84d',
             'startOffsetInAuthority': 3127,
             'endOffsetInAuthority': 3246,
             'startLine': 36,
             'endLine': 36,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'},
            {'sourceUnitID': 'hub:unit:01f61d9f42ae01b28f2c0cd86f00334579e8a016b5c2b852ba33a7e84b18da9a',
             'startOffsetInAuthority': 3246,
             'endOffsetInAuthority': 3392,
             'startLine': 37,
             'endLine': 37,
             'authorityTextSha256': 'cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4'}]}
SNAPSHOTS = {'data/interim/datasets/ciroh_hydroshare_corpus.json': '51453913c034c49c1751db1f111ebdc7d2c87e4cd6f8ce8573aee29d91338992',
 'data/interim/coderepos/ciroh_github_corpus.json': 'be5747c29f992362a545f9ff0600b4e4e74b560395e2aecfbf3a1a85f04f0c1c',
 'data/interim/documents/ciroh_hub_corpus.json': 'ea2d7a56e5fe2621b8a58405318efae3b178699355f85691bafa3e450aff8baa'}


def rebuild_selected(root):
    """Read only the three frozen owners, construct requests, and fail on drift."""
    from src.extraction.llm.datasets import request_contract as hs
    from src.extraction.llm.coderepos import request_contract as gh
    from src.extraction.llm.documents import request_contract as hub
    from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units
    from src.extraction.llm.coderepos.source_units import read_repository_sources
    from src.extraction.llm.documents.source_units import read_page_source_units
    corpora = []
    for relative, expected in SNAPSHOTS.items():
        raw = (root / relative).read_bytes()
        if digest(raw) != expected:
            raise ValueError("corpus_snapshot_drift:" + relative)
        corpora.append(json.loads(raw))
    resource = next(r for r in corpora[0] if r['resource_id'] == '7d960b7fdfee480895fd845bade1b75a')
    provenance = {"snapshotID": "sha256:" + next(iter(SNAPSHOTS.values())),
                  "sourceVersion": "2024-09-16T20:16:47.723282Z"}
    owner = resource['resource_id']
    abstract = build_abstract_source_unit(resource, accepted_owner_id=owner, provenance=provenance)
    absent = read_readme_source_units(None, accepted_owner_id=owner, provenance=provenance, required=False)
    requests = {"HS-01": hs.build_request(accepted_owner_id=owner, trusted_provenance=provenance,
        abstract_results=[abstract], readme_results=[absent], selected_unit_ids=[u['sourceUnitID'] for u in SELECTIONS['HS-01']], input_complete=True)}
    repo = next(r for r in corpora[1]['repos'] if r['repo_id'] == 921792119)
    reader = read_repository_sources(repo, root / 'data/raw/coderepos')
    expected_diagnostics = [('README.md', 4, None), ('README.md', 86, None),
                            ('examples/notebooks/nwm_usgs_streamflow_plot.ipynb', 1, 0)]
    if [(d.get('path'), d.get('startLine'), d.get('cellIndex')) for d in reader['diagnostics']] != expected_diagnostics or any(
            d.get('status') != 'needs_review' or d.get('reason') != 'content_kind_or_purpose_requires_review' for d in reader['diagnostics']):
        raise ValueError('github_diagnostics_drift')
    accepted = {k: reader['sourceUnits'][0][k] for k in ('canonicalArtifactID', 'repo_id', 'full_name', 'frozenCommitSha')}
    requests['GH-01'] = gh.build_request(reader, accepted_repository=accepted,
        selected_unit_ids=[u['sourceUnitID'] for u in SELECTIONS['GH-01']], input_complete=False)
    page = next(p for p in corpora[2]['pages'] if p['canonical_url'] == 'https://hub.ciroh.org/blog/aorc-data-access')
    reader = read_page_source_units(page)
    if [(d.get('sourceLine'), d.get('status'), d.get('reason')) for d in reader['diagnostics']] != [(11, 'needs_review', 'uncertain_markup_visibility')]:
        raise ValueError('hub_diagnostics_drift')
    requests['HUB-01'] = hub.build_request(page, reader, accepted_page_id='hub:page:83a1aceb2c34ed513d83',
        selected_unit_ids=[u['sourceUnitID'] for u in SELECTIONS['HUB-01']], input_complete=False)
    for name, graph, oid, cls in [
        ('HS-01','datasets/hydroshare_nodes_edges_v016.json',owner,'DatasetResource'),
        ('GH-01','coderepos/github_nodes_edges.json','github:repo:921792119','Repository'),
        ('HUB-01','documents/ciroh_hub_nodes_edges.json','hub:page:83a1aceb2c34ed513d83','DocumentationPage')]:
        nodes = json.loads((root / 'data/interim' / graph).read_bytes())['nodes']
        found = [n for n in nodes if n.get('id') == oid]
        if len(found) != 1 or found[0].get('class') != cls:
            raise ValueError('accepted_owner_drift')
        verify_selection(requests[name], SELECTIONS[name], oid)
    return requests


def write_local_preflight(root):
    """Write only prospective offline artifacts to the fixed ignored pilot path."""
    requests = rebuild_selected(root)
    summary = {}
    for name, ceiling in [('HS-01',4096), ('GH-01',3072), ('HUB-01',8192)]:
        result = build_preflight(requests[name], output_ceiling=ceiling)
        folder = root / 'var/study2_step12c/preflight' / name
        folder.mkdir(parents=True, exist_ok=True)
        for filename, data in [('semantic-request.json',result['semanticRequestBytes']),
                               ('provider-input.txt',result['inputBytes']), ('provider-envelope.json',result['wireBytes'])]:
            (folder / filename).write_bytes(data)
        meta = {k:v for k,v in result.items() if k not in ('semanticRequestBytes','inputBytes','wireBytes','envelope')}
        # One token per UTF-8 byte is a conservative content allowance, not an
        # exact tokenizer count or a guarantee about undocumented API overhead.
        meta['tokenEstimate'] = {'method':'UTF-8-byte allowance; model tokenizer unverified',
            'inputPlusSchemaAllowance':result['inputByteCount'] + result['schemaByteCount'],
            'providerOverhead':'unknown; approval requires additional margin'}
        (folder / 'preflight.json').write_bytes(canonical(meta))
        (folder / 'request-result.json').write_bytes(canonical(requests[name]))
        summary[name] = meta
    return summary


if __name__ == '__main__':
    from pathlib import Path
    print(json.dumps(write_local_preflight(Path(__file__).resolve().parents[3]), indent=2))
