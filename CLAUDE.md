# ADR Research Project — Claude Context

## Project Overview
FDA Adverse Drug Reaction (ADR) detection system using FAERS (FDA Adverse Event Reporting System) data.
Research focus: signal detection, MedDRA coding, embedding-based retrieval, knowledge graphs.

## Pipeline
1. **Data Prep**: `FAERS_Prep.ipynb` → raw FAERS quarterly CSVs → cleaned dataframes
2. **Embedding**: `finetune_BGE_base.ipynb` / `finetune_embedding_large.ipynb` → fine-tuned BGE-M3 model
3. **Vector Store**: `ADR_LanceDB.ipynb` → LanceDB vector database at `trn_lancedb/`
4. **Retrieval**: `ADR_inference.ipynb` → RAG-based ADR lookup pipeline
5. **Knowledge Graph**: `FAERS_Graph_prep.ipynb` → `ADR_KG/` directory

## Key Data Files
- `adr_all_new_up2_26q1.pkl` — latest processed FAERS dataset (2026 Q1)
- `adr_trn_tst.pkl` — train/test split
- `faers_new/` — raw quarterly FAERS downloads
- `trn_lancedb/` — BGE-M3 vector database (training set)
- `bge_m3_triplet_finetuned_SOC_bf16.pt` — fine-tuned BGE-M3 checkpoint

## Conventions
- MedDRA PT codes: lowercase strings (e.g., `'myopathy'`)
- Drug names: generic names in lowercase (FDA UNII preferred)
- SOC codes: use `mdhier_pt_soc.pkl` for hierarchy mappings
- Models save checkpoints to `bge_adr_base*/` and `bge_large*/` directories

## Active Research Directions
- FAERS-based ADR signal detection (disproportionality analysis: PRR, ROR)
- BGE-M3 fine-tuned on ADR triplets for semantic similarity
- Multi-label SOC classification (see `Centriod_ADR_cls.ipynb`)
- Knowledge graph for drug-event relationships
- Federated learning for privacy-preserving ADR detection (FedLLM proposal)

## Do Not
- Modify files in `faers/`, `faers_all/`, `aers_all/` (raw archives)
- Use pandas < 2.0 API
- Commit model checkpoints or large pkl files to git

## External Resources
- FAERS quarterly downloads: https://fis.fda.gov/extensions/FPD-QDE-FAERS
- MedDRA hierarchy browser: https://www.meddra.org
- RxNorm API: https://rxnav.nlm.nih.gov
