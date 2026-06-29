# ADR Research Project — Claude Context

## Project Overview
FDA Adverse Drug Reaction (ADR) detection system using FAERS (FDA Adverse Event Reporting System) data.
Research focus: signal detection, MedDRA coding, embedding-based retrieval, knowledge graphs.

## Pipeline
1. **Data Prep**: from raw FAERS quarterly .asc files to pandas dataframe
2. **BM25 Retriever**: Indexed BM25 retriever on training data
3. **Vector Store**: LanceDB vector database
5. **Knowledge Graph**: see project url: [GraphRAG App](nexusmed.ai)

## Key Data Files
- `adr_trn_tst.pkl` — train/test split
- `faers_new/` — raw quarterly FAERS downloads after 2012Q4
- `faers_old/` — raw quarterly FAERS downloads before 2012Q4
- `trn_lancedb/` — BGE-M3 vector database (training set)

## Conventions
- MedDRA PT codes: lowercase strings (e.g., `'myopathy'`)
- Drug names: generic names in lowercase (FDA UNII preferred)
- SOC codes: use `mdhier_pt_soc.pkl` for hierarchy mappings
- Embedding models checkpoints

## Active Research Directions
- FAERS-based ADR signal detection (disproportionality analysis: PRR, ROR)
- Fine-tuned embedding model with closed domain ADR triplets for semantic similarity search
- Multi-label SOC classification
- Knowledge graph for drug-event relationships

## External Resources
- FAERS quarterly downloads: https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html
- MedDRA hierarchy browser: https://www.meddra.org
- RxNorm API: https://rxnav.nlm.nih.gov
