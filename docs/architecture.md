# FieldGuard — System Architecture & Verification Pipeline

## 1. Architectural Overview

**FieldGuard** is a condition-aware numerical claim verification framework designed for government-scheme Question Answering using Retrieval-Augmented Generation (RAG). Unlike standard RAG pipelines or naive numerical fact-checkers that check only whether a claimed number appears somewhere in a retrieved chunk, FieldGuard decomposes every candidate claim and every trusted policy rule into structured semantic, contextual, and temporal dimensions before assigning a formal verdict.

```mermaid
flowchart TD
    subgraph Phase1_2["Phases 1 & 2: Corpus Acquisition & Extraction"]
        A["Official PMFBY Sources (PDFs & HTML)"] --> B["Acquisition & SHA-256 Manifest (source_manifest.py)"]
        B --> C["PDF Page & Table Extractor (document_extraction.py)"]
        C --> D["Paragraph Chunks (chunks.jsonl)"]
        C --> E["Header-Coupled Table Rows (table_rows.jsonl)"]
    end

    subgraph Phase4_5["Phases 4 & 5: Evidence Store & Multi-Paradigm Retrieval"]
        D --> F["Trusted Evidence Store (evidence_store.py)"]
        E --> F
        F --> G1["Semantic Dense Retriever (all-MiniLM-L6-v2)"]
        F --> G2["Lexical BM25 Retriever (Numeric-Preserving)"]
        F --> G3["Table-Aware Structured Retriever"]
        G1 --> G4["Hybrid RRF Retriever (hybrid.py)"]
        G2 --> G4
        G3 --> G4
    end

    subgraph Phase6_10["Phases 6 & 10: Claim Parsing & Condition-Aware Verification"]
        H["User Question + Candidate Numerical Claim"] --> I1["Parser A: Deterministic Rule-Based Parser"]
        H -.-> I2["Parser B: Optional LLM JSON Parser (Schema-Guarded)"]
        I1 --> J["Validated ParsedClaim Schema"]
        I2 -.-> J
        G4 --> K["FieldGuardVerifier (verifier.py)"]
        J --> K
        K --> L1["1. Provenance & Trust Check"]
        L1 --> L2["2. Evidence Sufficiency & Conflict Check"]
        L2 --> L3["3. Condition Matcher (Crop, Season, Geography)"]
        L3 --> L4["4. Qualification & Cap Condition Matcher"]
        L4 --> L5["5. Temporal & Policy-Version Resolver"]
        L5 --> L6["6. Numeric Normalizer & Operator Comparator"]
    end

    subgraph Verdicts["Four Formal Verdicts"]
        L6 --> V1["SUPPORTED"]
        L6 --> V2["CONTRADICTED"]
        L6 --> V3["WRONG_CONTEXT"]
        L6 --> V4["UNVERIFIABLE"]
    end
```

---

## 2. Core Modules (`src/fieldguard/`)

| Module | Responsibility | Key Classes / Functions |
| :--- | :--- | :--- |
| `src/fieldguard/source_manifest.py` | Immutable document metadata, SHA-256 verification, version and effective-date discipline | `SourceDocumentMetadata`, `SourceManifest`, `compute_file_sha256` |
| `src/fieldguard/data_acquisition.py` | Bounded HTTP/offline corpus acquisition, PDF header/signature verification, JSONL audit logging | `run_acquisition_pipeline` |
| `src/fieldguard/document_extraction.py` | Physical vs. printed PDF page extraction, section heading tracking, extraction warning logs | `parse_pdf_pages_from_bytes`, `run_extraction_pipeline` |
| `src/fieldguard/table_extraction.py` | Table row serialization with explicit column header coupling and missing-header rejection | `extract_table_units_from_page_tables` |
| `src/fieldguard/chunking.py` | Provenance-preserving paragraph chunking | `chunk_page_blocks_into_units` |
| `src/fieldguard/evidence_schema.py` | Schemas and validators for `ExtractedEvidenceUnit` and `StructuredPolicyRule` | `ExtractedEvidenceUnit`, `StructuredPolicyRule`, `validate_evidence_unit_schema` |
| `src/fieldguard/evidence_store.py` | Indexed store of evidence units and verified structured rules; blocks unverified sources | `EvidenceStore`, `build_default_evidence_store` |
| `src/fieldguard/retrieval/` | Semantic (`all-MiniLM-L6-v2`), Lexical (`BM25`), Table-Aware, and Hybrid (`RRF`) retrievers | `SemanticRetriever`, `LexicalBM25Retriever`, `TableAwareRetriever`, `HybridRetriever` |
| `src/fieldguard/numeric_normalizer.py` | Normalization of percentages, decimals, words, ratios (`50:50`), ranges, inequalities, and INR units | `normalize_number_string`, `compare_numeric_claim_to_rule` |
| `src/fieldguard/claim_parser.py` | Deterministic rule-based parser producing `ParsedClaim` | `DeterministicClaimParser`, `ParsedClaim` |
| `src/fieldguard/claim_parser_llm.py` | Optional LLM JSON parser with strict schema validation and unsupported-inference stripping | `LLMClaimParser`, `detect_unsupported_llm_inferences` |
| `src/fieldguard/condition_matcher.py` | Explicit matching across scheme, rule parameter, crop category, season, geography, and qualification | `match_claim_conditions_to_rule` |
| `src/fieldguard/temporal_resolver.py` | Policy-version and effective-date resolution without conflating `publication_date` and `effective_from` | `resolve_temporal_applicability` |
| `src/fieldguard/verifier.py` | Core decision engine mapping evidence candidates and condition checks to the four verdicts | `FieldGuardVerifier`, `VerifierConfig` |
| `src/fieldguard/evaluation/` | Retrieval metrics, verification metrics, cluster bootstrap CIs, ablations, and error analysis | `run_complete_evaluation_pipeline` |

---

## 3. Decision Priority Order in `FieldGuardVerifier`

To prevent both false support (`SUPPORTED` when evidence is wrong-context or insufficient) and false contradiction (`CONTRADICTED` when evidence is merely absent or from another policy version), `FieldGuardVerifier` evaluates retrieved evidence in a strict hierarchical order:

1. **Parse Integrity & Required Scope Check:** If the candidate claim is malformed (`parse_status == "failed_malformed"`), lacks a recognizable numerical claim, or omits an essential scope dimension (`crop_category` or `season` when required by the policy parameter), return `UNVERIFIABLE`.
2. **Evidence Presence & Provenance Validation:** Filter retrieved items to those backed by `verification_status == "verified"` documents in `SourceManifest`. If no verified evidence units or structured rules on the queried `rule_parameter` are retrieved, return `UNVERIFIABLE`.
3. **Rule-Parameter Partitioning:** Partition retrieved trusted rules on the same `rule_parameter` into:
   - **Condition-Aligned Rules:** Rules matching `crop_category`, `season`, `geography`, `qualification`, and `temporal` scope.
   - **Temporal-Mismatch Rules:** Rules matching semantic conditions and number, but failing `temporal_resolver` with `unverifiable_*` (e.g., applying a 2023 historical rule to an unverified current-policy query).
   - **Wrong-Context Rules:** Rules where either (a) the claimed numerical value matches a rule belonging to a *different* crop category, season, geography, policy version, or an omitted/contradicted qualification, or (b) all retrieved rules on the parameter belong to a mismatched context.
4. **Conflict Detection:** If two or more condition-aligned rules from verified sources assert mutually incompatible numerical values (e.g., `3.0%` vs `5.0%` in conflicting pilot addenda), return `UNVERIFIABLE` with `conflicting_retrieved_evidence`.
5. **Verdict Assignment on Condition-Aligned Rules:**
   - If a condition-aligned rule matches the claimed numerical value, unit, and operator $\rightarrow$ `SUPPORTED`.
   - If a condition-aligned rule has a different numerical value (and the claimed value actually matches a distractor rule from another category/season/geography in the retrieved set) $\rightarrow$ `WRONG_CONTEXT`.
   - Otherwise, if the condition-aligned rule directly refutes the claimed value or inequality operator $\rightarrow$ `CONTRADICTED`.
