#!/usr/bin/env python3
"""Fetch the real ego-depletion literature corpus from PubMed (NCBI E-utilities).

Every abstract in the corpus is the genuine published abstract, fetched live
from PubMed and stored with full provenance (PMID, DOI, journal, year, URL).
Nothing in the `abstract` field is synthetic.

The only curated fields are `role` and `ingest_order` (which stage of the
belief-revision timeline the paper belongs to) — dataset annotation, not paper
content.

Usage:
    python scripts/fetch_domain_corpus.py [--out data/domain/corpus.json]
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# The ego-depletion belief-revision timeline. `search` is a PubMed query
# expected to resolve to exactly the intended paper; `expect_year` guards
# against wrong hits. `role` is our curated annotation of the paper's
# evidential role; `ingest_order` is the chronological ingestion sequence used
# by the domain eval.
PAPERS = [
    dict(
        key="baumeister1998",
        search="ego depletion active self limited resource[Title] AND Baumeister[Author]",
        expect_year=1998,
        role="original_finding",
        ingest_order=1,
    ),
    dict(
        key="hagger2010",
        search="Ego depletion and the strength model of self-control[Title] AND meta-analysis[Title]",
        expect_year=2010,
        role="supporting_meta_analysis",
        ingest_order=2,
    ),
    dict(
        key="carter2014",
        search="Publication bias and the limited strength model of self-control[Title] AND Carter[Author]",
        expect_year=2014,
        role="bias_critique",
        ingest_order=3,
    ),
    dict(
        key="carter2015",
        search="series of meta-analytic tests of the depletion effect[Title]",
        expect_year=2015,
        role="corrective_meta_analysis",
        ingest_order=4,
    ),
    dict(
        key="hagger2016",
        search="Multilab Preregistered Replication of the Ego-Depletion Effect[Title]",
        expect_year=2016,
        role="failed_replication",
        ingest_order=5,
    ),
    # Note: the Baumeister & Vohs (2016) "Misguided Effort With Elusive
    # Implications" commentary has no abstract on PubMed, so the rebuttal role
    # is filled by Cunningham & Baumeister (2016), which does.
    dict(
        key="cunningham2016",
        search="How to Make Nothing Out of Something[Title] AND Cunningham[Author]",
        expect_year=2016,
        role="rebuttal_commentary",
        ingest_order=6,
    ),
    dict(
        key="friese2019",
        search="Is Ego Depletion Real[Title] AND Analysis of Arguments[Title]",
        expect_year=2019,
        role="methodological_review",
        ingest_order=7,
    ),
    dict(
        key="dang2021",
        search="Multilab Replication of the Ego Depletion Effect[Title] AND Dang[Author]",
        expect_year=2021,
        role="partial_replication",
        ingest_order=8,
    ),
    dict(
        key="vohs2021",
        search="Multisite Preregistered Paradigmatic Test of the Ego-Depletion Effect[Title]",
        expect_year=2021,
        role="definitive_multisite_test",
        ingest_order=9,
    ),
]


def esearch(term: str) -> list[str]:
    r = requests.get(
        f"{EUTILS}/esearch.fcgi",
        params={"db": "pubmed", "term": term, "retmode": "json", "retmax": 5},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["esearchresult"]["idlist"]


def efetch(pmid: str) -> dict:
    r = requests.get(
        f"{EUTILS}/efetch.fcgi",
        params={"db": "pubmed", "id": pmid, "retmode": "xml"},
        timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.text)
    art = root.find(".//Article")
    if art is None:
        raise ValueError(f"no Article element for PMID {pmid}")

    title = "".join(art.find("ArticleTitle").itertext()).strip()

    # Abstracts may be sectioned (BACKGROUND/METHODS/...); keep the labels.
    parts = []
    for ab in art.findall(".//Abstract/AbstractText"):
        label = ab.get("Label")
        text = "".join(ab.itertext()).strip()
        parts.append(f"{label}: {text}" if label else text)
    abstract = "\n".join(parts)

    year_el = art.find(".//JournalIssue/PubDate/Year")
    if year_el is None:
        year_el = root.find(".//PubMedPubDate[@PubStatus='pubmed']/Year")
    year = int(year_el.text)

    journal = art.findtext(".//Journal/Title", default="")
    authors = []
    for a in art.findall(".//AuthorList/Author"):
        last, init = a.findtext("LastName"), a.findtext("Initials")
        if last:
            authors.append(f"{last} {init or ''}".strip())
    doi = None
    for aid in root.findall(".//ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = aid.text
    return dict(
        pmid=pmid,
        title=title,
        abstract=abstract,
        year=year,
        journal=journal,
        authors=authors,
        doi=doi,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/domain/corpus.json")
    args = ap.parse_args()

    corpus = []
    for spec in PAPERS:
        ids = esearch(spec["search"])
        time.sleep(0.4)  # NCBI: max 3 req/s without an API key
        if not ids:
            print(f"FAIL {spec['key']}: no PubMed hits for {spec['search']}", file=sys.stderr)
            return 1
        rec = None
        for pmid in ids:
            cand = efetch(pmid)
            time.sleep(0.4)
            if cand["year"] == spec["expect_year"] and cand["abstract"]:
                rec = cand
                break
        if rec is None:
            print(f"FAIL {spec['key']}: no hit with year={spec['expect_year']} and an abstract", file=sys.stderr)
            return 1
        rec.update(
            paper_id=spec["key"],
            role=spec["role"],
            ingest_order=spec["ingest_order"],
            source="pubmed",
        )
        corpus.append(rec)
        print(f"ok  {spec['key']:16s} PMID {rec['pmid']}  {rec['year']}  {rec['title'][:70]}")

    corpus.sort(key=lambda r: r["ingest_order"])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, indent=2, ensure_ascii=False))
    print(f"\nwrote {len(corpus)} papers -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
