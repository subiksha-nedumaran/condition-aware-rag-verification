# FieldGuard Methodology and Experimental Design

## 1. Problem Formulation and Mathematical Framework

In Retrieval-Augmented Generation (RAG) systems deployed for public policy and insurance schemes, answers frequently assert numerical entitlements, premiums, indemnity rates, or statutory timelines. When querying government policy guidelines (such as the *Pradhan Mantri Fasal Bima Yojana*, PMFBY), documents contain dense multi-row tables and conditional provisions where identical or similar numerical values apply under strictly distinct conditions (e.g. 2.0% for Kharif food grains, 1.5% for Rabi food grains, 5.0% for commercial/horticultural crops, 90:10 subsidy sharing in North Eastern States vs 50:50 in General States).

Standard RAG architectures verify claims primarily via lexical matching, unconstrained semantic similarity, or ungrounded generative prompting. Consequently, an ordinary RAG verifier accepts a claim merely because a number (e.g., $5.0\%$) and key scheme tokens appear somewhere within a retrieved 500-token text chunk, even when the number governs an entirely different crop, season, or policy year.

### Formal Definition
Let $q$ denote a natural language policy query, and let $c$ denote a candidate numerical claim.
The claim parser maps $(q, c)$ into a structured tuple:
$$c = \langle v_c, u_c, \text{op}_c, \kappa_c, \sigma_c, \gamma_c, \tau_c, \beta_c, \pi_c \rangle$$
where:
- $v_c \in \mathbb{R}$ is the primary numerical value,
- $u_c \in \mathcal{U}$ is the measurement unit (e.g. `percent`, `days`, `weeks`, `hectares`),
- $\text{op}_c \in \{\le, \ge, <, >, =\}$ is the comparison operator,
- $\kappa_c \in \mathcal{K}$ is the crop or entity category (e.g. `food_grain_and_oilseed`, `commercial_and_horticultural`),
- $\sigma_c \in \mathcal{S}$ is the applicable season (e.g. `kharif`, `rabi`, `annual`),
- $\gamma_c \in \mathcal{G}$ is the geographic jurisdiction (e.g. `all_india`, `north_eastern_states`, `general_states`),
- $\tau_c = (t_{\text{ver}}, t_{\text{eff}})$ is the requested temporal scope and effective date,
- $\beta_c \in \mathcal{B}$ is the calculation basis or denominator (e.g. `sum_insured`, `actuarial_rate`, `normal_premium_subsidy`),
- $\pi_c \in \mathcal{P}$ is any statutory qualification (e.g. `or_actuarial_rate_whichever_is_less`).

Similarly, the verified corpus $\mathcal{D}$ consists of structured rules $r \in \mathcal{R}$ extracted from authenticated policy sources:
$$r = \langle v_r, u_r, \text{op}_r, \kappa_r, \sigma_r, \gamma_r, \tau_r, \beta_r, \pi_r, \text{status}_r, \text{conflict}_r \rangle$$

The goal of condition-aware verification is to evaluate the mapping $f(c, \mathcal{D}) \to \mathcal{V}$, where $\mathcal{V} = \{\text{SUPPORTED}, \text{CONTRADICTED}, \text{WRONG\_CONTEXT}, \text{UNVERIFIABLE}\}$.

---

## 2. The Four Primary Verdicts

FieldGuard defines four mutually exclusive, deterministic verdict labels:

1. **`SUPPORTED`**:
   The candidate claim agrees in value, unit, comparison operator, crop category, season, geography, calculation basis, qualification, and temporal scope with an authoritative official evidence record:
   $$\text{SUPPORTED} \iff \exists r \in \mathcal{D}_{\text{auth}} \text{ s.t. } \text{Match}_{\text{val}}(c, r) \land \text{Match}_{\text{ctx}}(c, r) \land \text{Match}_{\text{qual}}(c, r) \land \text{Match}_{\text{temp}}(c, r)$$

2. **`CONTRADICTED`**:
   Authoritative evidence exists for the exact claimed context (scheme, parameter, crop category, season, geography, and temporal period), but directly refutes the claimed number, operator, or qualification:
   $$\text{CONTRADICTED} \iff \exists r \in \mathcal{D}_{\text{auth}} \text{ s.t. } \text{Match}_{\text{ctx}}(c, r) \land \text{Match}_{\text{temp}}(c, r) \land \neg \left(\text{Match}_{\text{val}}(c, r) \land \text{Match}_{\text{qual}}(c, r)\right)$$

3. **`WRONG_CONTEXT`**:
   The claimed numerical value and unit exist in the verified corpus, but apply to a demonstrably different context (e.g. a different crop category, different season, different geographic region, or different policy version):
   $$\text{WRONG\_CONTEXT} \iff \exists r \in \mathcal{D}_{\text{auth}} \text{ s.t. } \text{Match}_{\text{val}}(c, r) \land \text{Match}_{\text{param}}(c, r) \land \neg \text{Match}_{\text{ctx}}(c, r)$$

4. **`UNVERIFIABLE`**:
   The available evidence is insufficient, ambiguous, contradictory across authoritative sources without a resolution rule, or unverified (e.g. unauthenticated secondary sources, unreleased future policy editions). FieldGuard abstains rather than assigning false support or hallucinating a contradiction.

---

## 3. Retrieval Architecture

FieldGuard implements four comparative retrieval modalities:

### A. Dense Semantic Retrieval
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense representations).
- **Execution:** Pure CPU safetensors inference with L2-normalized embeddings and exact inner-product search (equivalent to FAISS `IndexFlatIP`).
- **Caching:** SHA-256 validated corpus embedding cache (`cache/embeddings/minilm_l6_v2_corpus_cache.npz`).

### B. Lexical Retrieval (BM25)
- **Tokenization:** Case-folded, punctuation-stripped, alphanumeric unigrams and bigrams.
- **Scoring:** Okapi BM25 ($k_1 = 1.5, b = 0.75$) with exact matching on statutory numbers, percentages, and acronyms.

### C. Table-Aware Retrieval
- **Representation:** Structured JSONL records preserved at the table-row level with explicit column-header-to-cell key-value pairs.
- **Matching:** Composite scoring prioritizing row headers, parameter types, crop categories, and seasons.

### D. Hybrid Retrieval (Reciprocal Rank Fusion)
- Combines rankings from semantic, lexical, and table retrieval using Reciprocal Rank Fusion (RRF):
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{sem}, \text{lex}, \text{tab}\}} \frac{w_m}{k_{\text{rrf}} + \text{rank}_m(d)}$$
  with $k_{\text{rrf}} = 60$, $w_{\text{sem}} = 1.0$, $w_{\text{lex}} = 1.0$, $w_{\text{tab}} = 1.5$.

---

## 4. Verification Engine: 10-Step Decision Procedure

When candidate evidence is retrieved, the verifier executes the following strict decision sequence:

1. **Claim Normalization & Provenance Audit:** Parse the claim into typed fields. Verify that all retrieved evidence units exist in the verified store and have verified source provenance.
2. **Numeric Extraction & Unit Equivalence:** Normalize numbers and units. Enforce strict type safety: percentages ($2\%$) are never equated with dimensionless decimals ($0.02$).
3. **Operator Validation:** Distinguish inequalities ($\le, \ge, <, >$) from exact equality ($=$). Prepositional clauses (*"under PMFBY"*) are explicitly distinguished from inequality operators (*"under 2%"*).
4. **Crop Category Matching:** Verify category compatibility. Food grains/oilseeds do not inherit commercial/horticultural rules.
5. **Season Matching:** Verify seasonal applicability. Annual rules apply across seasons only for annual crops.
6. **Geographic Scope Validation:** Match national, regional (NER), and state-level jurisdictions.
7. **Temporal Resolution:** Compare requested policy periods against source effective intervals. Historical guidelines (2016) are marked `historical_superseded` for current queries; unverified future policies (2026) trigger abstention.
8. **Qualification & Basis Verification:** Enforce statutory qualifications (e.g. *"or Actuarial rate, whichever is less"*). Unconditional flat rate assertions on capped rules trigger `CONTRADICTED`.
9. **Evidence Sufficiency & Conflict Resolution:** Check whether sufficient applicable evidence exists. If conflicting authoritative records disagree without an explicit supersession rule, flag conflict and abstain.
10. **Verdict Synthesis & Provenance Attribution:** Assign the final verdict, record contributing evidence IDs, log failed condition dimensions, and generate an auditable verification rationale.

---

## 5. Experimental Protocols and Evaluation Metrics

### Datasets and Splitting
- **Total Claims:** 240 claims grouped into 60 claim families.
- **Split:** Development set = 72 claims (18 families); Held-out test set = 168 claims (42 families).
- **Cluster Stratification:** All perturbations derived from the same original source provision belong to the same family and are strictly kept within the same partition, preventing data leakage across development and test sets.

### Key Metrics
1. **Classification Accuracy & Macro-F1:** Standard multi-class metrics across the 4 verdict classes.
2. **False-Support Rate (FSR):** Safety-critical metric defined strictly as:
   $$\text{FSR} = \frac{\text{Count}(\text{Predicted} = \text{SUPPORTED} \land \text{Gold} \ne \text{SUPPORTED})}{\text{Count}(\text{Gold} \ne \text{SUPPORTED})}$$
3. **Coverage:** Fraction of queries receiving a definitive verdict ($\text{SUPPORTED}, \text{CONTRADICTED}, \text{WRONG\_CONTEXT}$) vs abstaining ($\text{UNVERIFIABLE}$).
4. **Selective Accuracy:** Accuracy calculated strictly over covered (non-abstained) predictions.
5. **Retrieval Recall@k and Item Recall@k:** Proportion of queries and proportion of individual relevant evidence units retrieved in top-$k$.
6. **Statistical Uncertainty:** 95% confidence intervals estimated via 1,000 cluster-bootstrap resamples at the claim-family level.

