# Roadmap

This document outlines planned enhancements and future features for the PRISMA 2020 SLR Engine.

---

## v1.1 - Source Expansion

### 1. arXiv API Integration
**Priority:** High

Pull recent preprints from arXiv to capture latest research before formal publication.

- **Scope:** Last 1 year of preprints
- **Query:** Configurable search terms (blockchain, data management, provenance, etc.)
- **Rate Limit:** 1 request/3 seconds (arXiv public API)
- **Implementation:**
  ```python
  # Target: src/connectors/arxiv_connector.py
  # Already exists - just needs enabled config
  arxiv:
    enabled: true
    date_from: "2025-03-01"  # 1 year from now
    max_results: 500
  ```

### 2. PubMed Integration
**Priority:** High

Add PubMed/MEDLINE as a data source for biomedical literature.

- **API:** NCBI E-utilities (PubMed)
- **Formats:** MEDLINE, XML
- **Implementation:**
  - Create `src/connectors/pubmed_connector.py`
  - Add to sources.yaml:
    ```yaml
    pubmed:
      enabled: false
      email: "your@email.com"  # Required for NCBI
      queries:
        - query: "blockchain data management"
          max_results: 200
    ```

---

## v1.2 - Enhanced Screening

### 3. Multi-Model Classification
Support multiple ML backends for classification:
- SciBERT (current)
- BioBERT (for biomedical)
- PubMedBERT (specialized for medical literature)
- RoBERTa-base (general NLP)

### 4. Hybrid Screening
Combine ML classification with keyword-based rules for higher accuracy.

### 5. Full-Text Screening
- Download full PDFs when available
- Use OCR for scanned documents
- Enhanced extraction with layout-aware models

---

## v1.3 - Quality & Validation

### 6. Inter-Rater Reliability
- Calculate Cohen's Kappa between automated and manual screening
- Flag papers with low confidence for manual review

### 7. Risk of Bias Assessment
- Add ROBINS-I for non-randomized studies
- Add RoB 2 for randomized trials

### 8. Data Extraction Templates
- Customizable extraction forms
- PDF form generation for manual extraction

---

## v1.4 - Reporting Enhancements

### 9. Multiple Export Formats
- [x] Markdown
- [x] LaTeX
- [ ] Word (.docx)
- [ ] HTML
- [ ] PDF via LaTeX

### 10. Interactive Dashboard
- Web-based visualization
- Filtering and sorting
- Manual annotation tools

### 11. Citation Network Analysis
- Build citation graph from CrossRef/DataCite
- Visualize citation relationships
- Identify influential papers

---

## v2.0 - Advanced Features

### 12. LLM-Powered Extraction
Use large language models for:
- Automatic key findings extraction
- Methodology summarization
- Limitation identification

### 13. Systematic Review Updates
Track citations to included studies for:
- New related papers alerts
- Citation tracking for updated reviews

### 14. Collaborative Screening
- Multi-user support
- Conflict resolution workflow
- Progress tracking

---

## Backlog

Lower priority items for future consideration:

- Semantic search using embeddings
- Automated systematic map generation
- Protocol registration (PROSPERO)
- PRISMA 2020 checklist validation
- Network analysis visualization
- Meta-analysis integration

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to the project.

---

*Last Updated: March 2026*
