# GitHub Raw → Consolidated Corpus — Preprocessing Contract (Phase A)

**Study 2 — Knowledge-graph construction, deterministic layer (Module 3: Code Repository / GitHub)**

**Purpose.** This document is the *contract* for **Phase A** of the GitHub pipeline:
turning the frozen raw download (`data/raw/coderepos/{repo_name}/`) into a single,
stable, normalized corpus file (`data/interim/coderepos/ciroh_github_corpus.json`). It
specifies the output schema and every parse/normalize rule, so that **Phase B** (the
mapping `corpus → nodes/edges` with deterministic IDs and dual evidence) can operate
without ever re-opening the raw. It is also a manuscript-ready record of how the GitHub
layer is preprocessed, and the basis for the Codex implementation prompt.

**Frontier (read this first).** Phase A **parses and normalizes only**. It resolves
manifests, classifies lockfiles, derives `fileRole`, extracts the CFF model, deduplicates
entries *within* a repo, and records provenance paths. Phase A does **not** mint nodes or
edges, does **not** assign ontology classes/relations or inventory IDs, does **not** build
`EvidenceSpan` objects, and does **not** consolidate entities across repos. All of that is
Phase B. Keeping this boundary clean is what made the HydroShare extractor land without
surprises; the consolidated corpus is the single faithful source Phase B reads from.

---

## 1. Position in the pipeline

Three-level architecture per artifact type (unchanged from HydroShare):

1. **raw corpus** — `data/raw/coderepos/{repo_name}/` (frozen; gitignored; produced by the
   download notebook, which is shared/dissertation code).
2. **consolidated corpus** — `data/interim/coderepos/ciroh_github_corpus.json` (**this
   document's output**; gitignored; the repo ships the CODE that produces it, not the file).
3. **nodes/edges** — `data/interim/coderepos/github_nodes_edges.json` (Phase B output).

Unlike HydroShare (whose consolidated corpus already existed), GitHub had no preprocessing;
Phase A is the new step that builds level 2.

---

## 2. Raw input inventory

Per repo, `data/raw/coderepos/{repo_name}/` contains four notebook-generated JSON files
(schema fixed by the download code) plus a `contents/` tree of selected third-party files.

| File | Shape | Notes |
|---|---|---|
| `repo_metadata.json` | object | GitHub repo object, trimmed. `license` is an object or `null`; `topics` may be `[]`; `language`/`homepage`/`description` may be `null`; `fork` is a boolean (**no `parent` field is captured**). Embeds `contributors_summary` (top ≤10). |
| `archive_info.json` | object | `owner, repo_name, default_branch, frozen_commit_sha, downloaded_at_epoch, archive_format`. The `frozen_commit_sha` is the snapshot pin. |
| `files_manifest.json` | array | One entry per file in the repo: `{path, file_name, extension, size_bytes, downloaded, selection_reason}`. Lists **all** files (downloaded or not). |
| `contributors.json` | array | Full contributor list: `{id, login, html_url, type, contributions}`. `type ∈ {User, Bot}`. **No name/email/ORCID.** |
| `contents/` | tree | Only `downloaded:true` files, preserving relative paths: README, LICENSE, CITATION.(cff\|md), CHANGELOG, CONTRIBUTING, and the dependency/environment manifests, plus selected docs/notebooks. |

**Known raw-level coverage gaps (carried as documented limitations, not fixed here):**

- **Dockerfiles are not downloaded** (`dockerfile` is absent from the download whitelist).
  Their **existence** is visible in `files_manifest.json`; their **content** is not in the
  raw. `ExecutionEnvironment` (A-C04) therefore cannot be sourced from Dockerfiles; its real
  sources are `environment.yml`, `Pipfile [requires]`, `pyproject requires-python`, and
  `setup.cfg python_requires`. Re-downloading would touch the shared frozen corpus and the
  CIROH AI Bot v2 pipeline, so it is deferred; a future SHA-pinned supplementary fetch
  remains a cheap option if NGIAB environment provenance becomes central.
- **Non-standard environment filenames are not downloaded** (e.g. `pytorch.yml` in
  `LSTM-Tutorials`): only `environment.yml`/`.yaml` match. Some named conda envs will be
  absent. Documented as a coverage limitation.
- **Phase A dependency parsing covers Python ecosystems only.** Non-Python manifests
  (e.g. Rust `Cargo.toml`, JavaScript `package.json`) yield no dependencies by design, and
  `setup.py` files with non-literal/dynamic `install_requires` are deferred rather than
  executed, with the deferral tracked in `parse_warnings`.
- **`fork` parent is not captured** → `fork_parent` is always `null` deterministically
  (the `fork` boolean is reliable; the parent is deferred / E).

---

## 3. Conventions

**Idempotency & determinism.** Phase A is a pure function of the raw input: same raw → same
corpus, byte-stable ordering (sort repos by `name`; sort arrays by a stable key). No random
IDs, no network, no time-dependent values beyond what the raw already carries.
Deterministic ordering applies to structures Phase A constructs; raw text carried as evidence
such as lockfile `pinned_set_evidence` preserves original file order.

**Provenance preservation for Phase B.** Phase A does not build evidence objects, but it
records, for every normalized fact, the **manifest path** (and raw line where applicable)
under a `sources` / `source_path` field. This is exactly what Phase B needs to populate
`sourceLocation` (the provenance path) and `evidenceText` (the value). The raw line is kept
verbatim for line-based manifests, and reconstructed as faithful TOML for TOML-table
manifests because `tomllib` does not preserve source text, so Phase B's `evidenceText`
carries semantic value, not just a field path.

**Normalization principle.** Normalize only what is mechanical and reversible-by-record:
lower-casing package names for the dedup key while keeping the original spelling in `raw`;
splitting a requirement into structured fields while keeping the original string. Never
"correct" source data (e.g. swapped given/family names, typo'd logins) — that would bias
later consolidation; extract as-is and let Phase B / the agent layer reconcile.

**Within-repo dedup only.** Phase A collapses duplicate facts *inside one repo* (the same
dependency declared in three manifests → one entry with three `sources`). Cross-repo
identity (same person, same library node) is **not** touched here.

---

## 4. Output schema — `ciroh_github_corpus.json`

Top level: `{ "schema_version": "1.0.0", "repos": [ <repo_record>, ... ] }`.
`schema_version` versions the output schema; `phase_a_version` versions the parser logic.

A `<repo_record>` has the following stable shape. Every field is always present; absence is
encoded as `null` / `[]` / `false`, never as a missing key (so Phase B never branches on key
existence).

```jsonc
{
  "repo_id": 807668057,                       // GitHub numeric id (stable repo key)
  "name": "deep_bucket_lab",
  "full_name": "CIROH-UA/deep_bucket_lab",
  "html_url": "https://github.com/CIROH-UA/deep_bucket_lab",
  "description": "Model of water in/out of a bucket. Training an LSTM." ,  // | null
  "homepage": null,                           // | string
  "default_branch": "main",
  "language": null,                           // | string
  "topics": [],                               // [] | [string, ...]
  "fork": true,
  "fork_parent": null,                        // always null (parent not in raw)
  "archived": false,
  "disabled": false,
  "visibility": "public",
  "timestamps": { "created_at": "...", "updated_at": "...", "pushed_at": "..." },

  "github_stats": {                           // administrative — excluded from density numerator
    "size_kb": 19273, "stargazers_count": 0, "watchers_count": 0,
    "forks_count": 6, "open_issues_count": 0
  },

  "archive": {                                // from archive_info.json
    "frozen_commit_sha": "23b412d6...",
    "downloaded_at_epoch": 1777772571.18579,
    "archive_format": "zip"
  },

  "license": {                                // pass-through from repo_metadata; | null
    "key": "mit", "name": "MIT License", "spdx_id": "MIT",
    "url": "https://api.github.com/licenses/mit",
    "is_spdx": true,                          // false for NOASSERTION/null/custom (e.g. USDOC)
    "source_path": "repo_metadata.json:license"
  },

  "identifiers": [                            // collected repo identifiers (Phase B → Identifier)
    { "id_type": "repo_url", "value": "https://github.com/CIROH-UA/deep_bucket_lab",
      "source_path": "repo_metadata.json:html_url" },
    { "id_type": "commit_sha", "value": "23b412d6...",
      "source_path": "archive_info.json:frozen_commit_sha" }
    // CFF doi (if any) appended here too, id_type "doi"
  ],

  "contributors": [                           // from contributors.json (FULL list), login regime
    { "github_id": 44035137, "login": "jmframe",
      "html_url": "https://github.com/jmframe", "type": "User",
      "contributions": 41, "is_bot": false,
      "source_path": "contributors.json[0]" }
    // type=="Bot" → is_bot:true (Phase B excludes from Person)
  ],

  "files": {
    "total_count": 25,
    "downloaded_count": 5,
    "selection_reason_histogram": { "allowed_exact_filename": 3,
                                    "allowed_top_level_notebook": 1, "...": 1 },
    "has_dockerfile": false,
    "downloaded": [                           // only downloaded:true entries
      { "path": "README.md", "file_name": "README.md", "extension": ".md",
        "size_bytes": 5051, "selection_reason": "allowed_exact_filename",
        "file_role": "readme", "source_path": "files_manifest.json:README.md" }
      // ...
    ],
    "dockerfiles": [                          // existence-only (downloaded:false), no content
      // { "path": "Dockerfile", "file_name": "Dockerfile", "size_bytes": 3890 }
    ]
  },

  "dependencies": [                           // DIRECT package deps only (§6.4). Deduped within repo.
    { "name": "numpy", "raw": "numpy", "version_spec": null, "extras": [],
      "marker": null, "ecosystem": "pypi", "dep_group": "runtime", "is_vcs": false,
      "sources": [ { "manifest_path": "requirements.txt", "manifest_type": "requirements_txt",
                     "manifest_scope": "root", "raw_line": "numpy" } ] }
    // ...
  ],

  "repo_dependencies": [                      // VCS deps → repo→repo (§6.4, D4)
    { "name": "hypy", "vcs_url": "https://github.com/noaa-owp/hypy", "ref": "master",
      "subdirectory": "python", "egg": "hypy", "raw": "git+https://github.com/noaa-owp/hypy@master#egg=hypy&subdirectory=python",
      "dep_group": "runtime",
      "sources": [ { "manifest_path": "requirements.txt", "manifest_type": "requirements_txt",
                     "manifest_scope": "root",
                     "raw_line": "git+https://github.com/noaa-owp/hypy@master#egg=hypy&subdirectory=python" } ] }
  ],

  "execution_environment": [                  // §6.6 — conda env metadata + lockfiles-as-evidence + python constraints
    { "kind": "conda_env", "name": "deep_bucket_env",
      "channels": ["conda-forge", "defaults"], "python_version": "3.9", "prefix": null,
      "is_lock": false, "pinned_count": null, "pinned_set_evidence": null,
      "source_path": "environment.yml" }
    // lock variants carry the resolved set in pinned_set_evidence, NOT exploded into deps[]
  ],

  "citation": {                               // §6.5 (D7): present = parseable CFF exists; format ∈ {cff, md, none}
    "present": false, "format": "none", "placeholder": false, "source_path": null,
    "cff_version": null, "type": null, "title": null,
    "software_authors": [], "doi": null, "version": null, "date_released": null,
    "url": null, "repository_code": null, "repository": null,
    "keywords": [], "license": null, "abstract": null,
    "preferred_citation": {
      "type": null, "authors": [], "doi": null, "title": null, "journal": null,
      "year": null, "volume": null, "number": null, "start": null, "end": null,
      "publisher": null, "url": null
    },
    "references": [
      { "type": null, "authors": [], "doi": null, "title": null, "journal": null,
        "year": null, "volume": null, "number": null, "start": null, "end": null,
        "publisher": null, "url": null }
    ]
  },

  "citation_md": null,                        // or { "present": true, "source_path": "CITATION.md", "deferred_to_llm": true }

  "software_metadata": [],                    // entries: {name, version, authors:[{name,email}], urls:{},
                                              //           license, manifest_type, source_path}

  "readme": {                                 // text carried for Phase B URL-typing + LLM layer
    "present": true, "source_path": "README.md",
    "text": "<full README text>",
    "deterministic_urls": {                   // mechanical regex extraction (typed by Phase B)
      "hydroshare": [], "github": [], "dois": [], "other": []
    }
  },

  "provenance": {
    "source_artifact": "https://github.com/CIROH-UA/deep_bucket_lab/tree/23b412d6...",
    "phase_a_version": "1.0.0",
    "parse_warnings": []                       // e.g. {file, issue}: setup.py dynamic, symlink env, FIXME cff
  }
}
```

`provenance.source_artifact` is the SHA-pinned canonical GitHub anchor for the frozen raw
snapshot, built from `html_url` and `archive.frozen_commit_sha`.

---

## 5. Processing rules — repository metadata, files, contributors

### 5.1 Repository core (from `repo_metadata.json` + `archive_info.json`)
Direct pass-through with null-safety. `repo_id = id`. Administrative counters go under
`github_stats` (signals the density-exclusion boundary; Phase B / the metric treats these as
non-informative). `license` is copied verbatim plus a derived `is_spdx` flag: `true` when
`spdx_id` is a real SPDX token, `false` for `null` / `"NOASSERTION"` / custom strings
(e.g. NOAA `USDOC`). Both `archive_info.frozen_commit_sha` and `html_url` are emitted into
`identifiers[]`.

### 5.2 Files & `fileRole` derivation (from `files_manifest.json`)
Emit `total_count`, `downloaded_count`, and a `selection_reason_histogram` over **all**
manifest entries (preserves the selection-policy contribution, e.g. deep_bucket_lab's 5/25).
Mint full `File` records (in `files.downloaded[]`) **only for `downloaded:true`** (decision
already ratified: non-downloaded files are counted, not nodalized). Record Dockerfile
existence separately in `files.dockerfiles[]` (from `downloaded:false` manifest entries) and
set `has_dockerfile`, with no content.

`file_role` is **derived** (the manifest gives `selection_reason`, not role), priority-ordered
on `file_name`/`extension`/`path` (lower-cased):

| Priority | Match | `file_role` |
|---|---|---|
| 1 | `readme*` | `readme` |
| 2 | `license*`, `licence*`, `copying*` | `license` |
| 3 | `citation.cff` | `citation_cff` |
| 4 | `citation`, `citation.md`, `citation.txt` | `citation_md` |
| 5 | `changelog*` | `changelog` |
| 6 | `contributing*` | `contributing` |
| 7 | `code_of_conduct*` | `code_of_conduct` |
| 8 | `security.md` | `security` |
| 9 | `dockerfile`, `dockerfile.*`, `containerfile` | `dockerfile` |
| 10 | `requirements*.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `pipfile`, `pipfile.lock` | `dependency_manifest` |
| 11 | `environment.yml`, `environment.yaml` | `environment_manifest` |
| 12 | ext `.ipynb` | `notebook` |
| 13 | path under `docs/`/`doc/`/`documentation/` with ext `.md`/`.rst`/`.markdown` | `documentation` |
| 14 | path under `examples/`/`tutorials/`/semantic folder with doc/notebook ext | `example` |
| 15 | ext `.py` | `source` |
| 16 | ext `.md`/`.rst`/`.markdown` (top-level) | `documentation` |
| 17 | else | `other` |

### 5.3 Contributors (from `contributors.json`)
Pass through the **full** list (not the ≤10 summary). Set `is_bot = (type == "Bot")`. Phase B
excludes bots from `Person` (ratified). These are the **GitHub-login** identity regime
(no name/email/ORCID). Duplicate humans across logins (e.g. `arpita0911patel` vs
`arpitapatel09` in awi-ciroh-image) are **left as-is** — seed-not-merge.

---

## 6. Processing rules — dependencies, environment, citation

### 6.1 Manifest discovery & path disambiguation
Walk `files.downloaded[]` for `file_role ∈ {dependency_manifest, environment_manifest}`.
Record each manifest's `path`. **Root-level** manifests describe the repo's own deps;
manifests under `docs/`, `examples/`, `tutorials/` describe doc-build / example deps. Phase A
tags each parsed manifest with `manifest_scope ∈ {root, docs, example}` (derived from path)
and, in `dependencies[].sources[]` / `repo_dependencies[].sources[]`, preserves the originating
manifest path and `manifest_scope`. Phase B may
prefer `root`-scope deps; Phase A does not drop non-root manifests, it labels them.

### 6.2 Lockfile vs direct classification (D1)
Each manifest is classified **direct** or **lock**. Only **direct** manifests feed
`dependencies[]` / `repo_dependencies[]`. **Lock** manifests feed `execution_environment[]`
with their resolved set carried in `pinned_set_evidence` (and `pinned_count`), **never
exploded** into per-package edges. Detection signals:

| Format | Lock signal |
|---|---|
| `environment.yml` | any dependency line with a build triple `name=version=build` (two `=`), **or** a `prefix:` field, **or** presence of system sentinels (`_libgcc_mutex`, `_openmp_mutex`). A hand-authored env has bare names or single-`=` pins and no `prefix`. |
| `requirements.txt` | an environment marker (`; python_version ...`) on (nearly) every line, **or** ≥ ~60 fully-pinned (`==`) entries including known-transitive packages — i.e. a `pip freeze` / `poetry export` dump. |
| `Pipfile.lock`, `poetry.lock`, `*-lock.yml` | by filename → always lock. |
| `Pipfile`, `pyproject.toml`, `setup.cfg`, `setup.py`, hand `requirements.txt`/`environment.yml` | direct. |

A manifest classified **lock** still contributes its **non-package metadata** to
`execution_environment` (env `name`, `channels`, `python_version`, `prefix`).

### 6.3 The unified requirement normalizer (D4)
Every direct dependency line, regardless of source format, is parsed into:

```
{ name, raw, version_spec|null, extras[], marker|null, ecosystem("pypi"|"conda"),
  is_vcs(bool), vcs_url|null, ref|null, subdirectory|null, egg|null }
```

Branching:
- **VCS form** (`git+https://…`, PEP 508 `name @ git+https://…@ref`, Poetry inline
  `{git="…", rev="…"}`) → `is_vcs:true`; route to **`repo_dependencies[]`** with `vcs_url`
  (normalized to `https://github.com/{owner}/{repo}`), `ref`, `subdirectory`, `egg`. Several
  point to in-corpus repos (e.g. `ciroh-ua/ngen-cal`, `noaa-owp/hypy`).
- **Package form** → `is_vcs:false`; route to **`dependencies[]`**. Parse PEP 508 specifiers
  (`==`, `~=`, `>=x,<y`, `!=`, bare), extras (`pkg[all]`), and markers (`; python_version…`).
  Conda lines use single-`=` pins; `pip:` subsection lines use PyPI `==`. Record `ecosystem`.
  `version_spec` keeps the full constraint string; `raw` keeps the original line.
- **Exclusions (never deps):** Python itself (`python`/`python_version` → `execution_environment`),
  C/Fortran libraries in `setup.py Extension(libraries=…)`, conda system libs in lock sets,
  and known build bootstrap backends (`pip`, `setuptools`, `wheel`, `poetry-core`,
  `hatchling`, `flit-core`, `pdm-backend`, `hatch-vcs`) even when they appear in
  `[build-system].requires`.

Dedup key = `(normalized_name, is_vcs, vcs_url_or_none)`. Within a repo, collapse to one entry
with merged `sources[]`; `dep_group` precedence on conflict: `runtime > optional > dev > build`.

### 6.4 Per-format parsers
- **`requirements.txt`** — line-based. Skip blank lines, full-line comments (`#…`), and
  `-r`/`-c`/`-e` include directives (record `-e .` as a self-reference note, not a dep). Strip
  inline `# comment`. Each remaining line → normalizer. Classify direct/lock first (§6.2).
- **`environment.yml`** (D5) — YAML. **Symlink guard:** if the file content is a single line
  that is a filesystem path with no YAML mapping (e.g. `../conda/conda-linux-64.lock.yml`),
  emit a `parse_warning` and skip (not a real env). Parse `name`, `channels`,
  `dependencies[]`. `dependencies` is a list of strings **and optionally one dict
  `{pip: [...]}`**. Skip commented entries (`# - pkg`). Conda string entries → `dependencies`
  (`ecosystem:"conda"`); `pip:` entries → `dependencies` (`ecosystem:"pypi"`). `python=X` →
  `execution_environment.python_version`. `name`/`channels`/`prefix` → `execution_environment`.
  If lock-classified, conda packages are **not** exploded; the resolved set goes to
  `pinned_set_evidence`.
- **`pyproject.toml`** — TOML. Detect backend: PEP 621 `[project]`, Poetry `[tool.poetry]`,
  or config-only (neither). 
  - PEP 621: `[project].dependencies` → runtime; `[project.optional-dependencies].*` →
    optional (group = table key); `[build-system].requires` → build. `requires-python` →
    `execution_environment` python constraint. Also capture `name`, `authors[{name,email}]`
    (→ `software metadata`, see note), `urls`.
  - Poetry: `[tool.poetry.dependencies]` (dict): `python` → execution env; string values →
    runtime; inline `{git=…}` → VCS. `[tool.poetry.group.*.dependencies]` / legacy
    `[tool.poetry.dev-dependencies]` → dev.
  - Config-only (e.g. only `[build-system]` + `[tool.black]`) → no runtime deps; record the
    build requires only.
- **`setup.cfg`** — INI via configparser. `[options].install_requires` (newline list, may
  include PEP 508 git deps) → runtime; `[options.extras_require].*` → optional/dev;
  `python_requires` → execution env. `[metadata]` → `name`, `author`/`author_email`
  (→ software metadata, name+email regime), `license`, `url`/`project_urls`.
- **`setup.py`** (D2) — **static AST only; never execute.** Parse the `setup(...)` call;
  extract `install_requires` / `extras_require` **only if they are literal lists/dicts**. If
  the argument is a name, comprehension, file read, or computed value, set
  `deps: deferred-unparseable` and emit a `parse_warning`. Never mine `import` statements or
  `Extension(libraries=…)`. Rely on a sibling `setup.cfg`/`pyproject` per §6.7 precedence.
- **`Pipfile`** — TOML. `[packages]` → runtime; `[dev-packages]` → dev; `[requires].python_version`
  → execution env. `[[source]]` ignored.
- **`Pipfile.lock`** — lock by filename → `execution_environment` evidence only (resolved set
  in `pinned_set_evidence`).

### 6.5 CITATION.cff (D7)
Parse **only files with `file_role:citation_cff`** as CFF 1.2.0 YAML.
`CITATION.md`/`CITATION.txt` (`file_role:citation_md`) are prose → recorded under
`citation_md` with `deferred_to_llm:true`, **not** parsed for structured authors/DOI.
The `citation` block has two axes: `present` means a parseable `CITATION.cff` exists, while
`format ∈ {cff, md, none}` records which citation file type is present. A Markdown-only
citation has `format:"md"` and `present:false`.

**Placeholder guard:** if `title`/author names are cffinit placeholders (`FIXME`, all-`FIXME`
authors, or the cffinit header comment with unfilled fields), set `citation.placeholder:true`
and do not populate `software_authors` (Phase B skips minting). Emit a `parse_warning`.

Extract the full model:
- **Top-level `authors`** → `software_authors[]` `{family_names, given_names, orcid|null,
  affiliation|null, email|null}` (name+ORCID±affiliation regime). Names extracted **as-is**
  even when given/family appear swapped in the source.
- **`preferred-citation`** → `preferred_citation` with the fixed key set
  `{type, authors:[{family_names, given_names, orcid}], doi, title, journal, year, volume,
  number, start, end, publisher, url}`. These authors are **paper authors** → Phase B routes
  them to the `Paper` stub, **not** to repo contributors. `doi` present → `Paper` keyed by DOI;
  text-only → deferred.
- **`references[]`** → additional `Paper`/work stubs with the same fixed key set
  (same DOI-or-deferred rule). CFF keys outside this fixed subset are ignored.
- **Top-level `doi`** → repo `Identifier` (id_type `doi`); Zenodo DOIs flag an `archivedAs`
  candidate for Phase B (D-20, E).
- **`version` / `date-released`** → `ModelVersion` seed (A-C10, E).
- **`url` / `repository-code` / `repository`** → captured distinctly. `repository` may point to
  **another corpus repo** (e.g. CFF 6 → `NGIAB-CloudInfra`) — a cross-repo reference for Phase B.
- **`keywords`** → `Subject` seeds; **`license`** → `License` seed; **`abstract`** → evidence text.

### 6.6 ExecutionEnvironment assembly
`execution_environment[]` aggregates, with `source_path` on each entry:
- conda `environment.yml` metadata (`name`, `channels`, `python_version`, `prefix`);
- `Pipfile [requires].python_version`; `pyproject requires-python`; `setup.cfg python_requires`
  (as `kind:"python_constraint"`);
- **lock-classified manifests** (conda export, pip lock, `Pipfile.lock`): `is_lock:true`,
  `pinned_count`, and the resolved set verbatim in `pinned_set_evidence` (carried, not exploded).
  `pinned_set_evidence` preserves original file order because the lock ordering is part of
  the evidence artifact.

Dockerfile-derived environments are **absent** (raw gap, §2).

### 6.7 Software metadata note (authors from pyproject/setup.cfg)
`name+email` author metadata from `pyproject [project].authors` and `setup.cfg [metadata]`
is recorded under the always-present repo-level `software_metadata[]` array with entries
`{name, version, authors:[{name,email}], urls:{}, license, manifest_type, source_path}`.
This is the third GitHub-side `Person` regime; Phase B seeds these as Person (name+email)
without merging.

---

## 7. Person identity regimes (D6)

Phase A records, but never merges, four author/contributor regimes; Phase B seeds each with
its regime tag and routes appropriately.

| Regime | Source | Carries | Phase B routing |
|---|---|---|---|
| GitHub login | `contributors.json` | login (no name/email) | `Person` + `hasContributor` (bots excluded) |
| name + ORCID (± affiliation) | CFF top-level `authors` | names, ORCID, affiliation | `Person` (software author); affiliation → `Organization` + `affiliatedWith` |
| name + email | `pyproject`/`setup.cfg` authors | names, email | `Person` (software author) |
| paper author | CFF `preferred-citation`/`references` authors | names (± ORCID) | attached to the **`Paper`** stub, **not** repo contributors |

---

## 8. Guards & edge cases (consolidated)

- **Symlink-as-text** environment file → skip with warning (env 7 case).
- **Commented manifest lines** (`# - pkg`, `#dep`) → skip.
- **CFF placeholder/template** (`FIXME`) → flag, do not seed authors.
- **`setup.py` dynamic / no `install_requires`** → `deferred-unparseable`, never execute.
- **Non-SPDX license** (`USDOC`, custom, `NOASSERTION`, null) → `is_spdx:false`; keep string.
- **Config-only `pyproject`** → no runtime deps; build requires only.
- **Sparse repo** (no manifest, no CFF — e.g. `awi-ciroh-image`) → yields repo core, license,
  contributors, downloaded files, identifiers; `dependencies`/`citation` empty. Never assume
  presence.
- **Non-standard env filename** (`pytorch.yml`) not in raw → coverage limitation, documented.
- **Swapped given/family names** in CFF → extract verbatim, no correction.
- **Duplicate logins** for one human → seed-not-merge.
- **`-e .` / self-reference** in requirements → noted, not a dependency.

---

## 9. What Phase A does NOT do (frontier with Phase B and the LLM layer)

- No node/edge minting, no ontology classes/relations/inventory IDs, no `EvidenceSpan`
  objects, no deterministic entity IDs — Phase B.
- No cross-repo consolidation (Person/Library/Tool/Repository identity) — later step.
- No URL **typing** (which README URL becomes `usesDataset` vs `referencesRepository`) —
  Phase A only extracts the URLs by regex into `readme.deterministic_urls`; Phase B types them
  (consistent with HydroShare C-D19).
- No prose interpretation: `RepositoryPurpose`, `Function`, `Algorithm`, `Workflow`,
  `usesTool`/`mentionsModel`, `implementsMethod`, `Variable`/`Parameter` — LLM layer. README
  and CITATION.md text are **carried** so the LLM layer reads them from the corpus.

---

## 10. Phase A self-validation checks (before Phase B)

- Every repo in `data/raw/coderepos/` produces exactly one `<repo_record>`; counts match.
- Every record has all schema keys present (null/[]/false for absent), so Phase B never
  branches on key existence.
- Every `dependencies[]` / `repo_dependencies[]` / `software_authors[]` / identifier entry has
  a non-empty `sources`/`source_path` (Phase B evidence depends on it).
- Every parsed manifest was classified direct **or** lock; lock manifests contributed **zero**
  package entries to `dependencies[]`.
- `files.downloaded_count` equals `len(files.downloaded)`; `total_count` equals the manifest
  length; histogram sums to `total_count`.
- `parse_warnings` enumerated for every skipped/deferred manifest (symlink, dynamic setup.py,
  FIXME cff) — none silently dropped.
- VCS deps normalized to a resolvable `vcs_url`; package deps carry an `ecosystem`.

---

## 11. Worked instantiation (the three sampled repos)

- **`deep_bucket_lab`** (fork, MIT, 5/25 downloaded): repo core + `github_stats`;
  `contributors` = jmframe/maoyab/leilaher (login regime; jmframe cross-links to a paper
  author); `files.downloaded` = CITATION.md (→ `citation_md`, deferred), LICENSE, README.md,
  the notebook, environment.yml; `citation.format = "md"`; `execution_environment` from
  `environment.yml` (`name:deep_bucket_env`, conda-forge/defaults, python 3.9, **direct** —
  hand-authored); `dependencies` from that env's conda packages. No `.cff`, no Dockerfile.
- **`awi-ciroh-image`** (not fork, BSD-3-Clause, sparse): repo core; six contributors incl.
  the `arpita0911patel`/`arpitapatel09` duplicate-login pair (seed-not-merge) and `pkdash`
  (cross-links to HydroShare); `files.downloaded` = LICENSE, README.md; **no manifests, no
  CFF** → `dependencies`/`citation` empty; `has_dockerfile:true` (existence only, content
  absent — A-C04 gap). Demonstrates the sparse-repo path.
- **`LSTM-Tutorials`** (fork, MIT): contributors whitelightning450/shahab122/savalann
  (savalann cross-links to the NGIAB CFF authors); `files.downloaded` = several notebooks,
  GettingStarted.md, LICENSE, README.md, requirements.txt; `dependencies` from
  `requirements.txt` (direct); the repo's `pytorch.yml` conda env is **absent** from raw
  (non-standard name) → documented coverage limitation.

---

*End of Phase A contract. Phase B (`ciroh_github_corpus.json` → nodes/edges, with inventory
IDs and dual evidence) is specified separately, mirroring `hydroshare_extraction_mapping.md`.*
