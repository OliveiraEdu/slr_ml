@startuml
skinparam rectangle<<hidden>> {
  backgroundColor transparent
  borderColor transparent
}

!define IDENTIFIED_COLOR #E3F2FD
!define SCREENING_COLOR #FFF3E0
!define INCLUDE_COLOR #E8F5E9
!define EXCLUDE_COLOR #FFEBEE
!define REVIEW_COLOR #F3E5F5

rectangle "PRISMA 2020 Flow Diagram - d-OSPv2 maDMP SLR" {

  rectangle "IDENTIFICATION" as ID {
    note
      <b>Records identified from databases</b>
      - IEEE Xplore
      - ACM Digital Library  
      - Web of Science
      - Scopus
      - arXiv
      
      <b>n=1,158</b> (after deduplication)
    end note
  }

  rectangle "SCREENING" as SCR {
    note
      <b>LLM Agentic Screening</b>
      Model: Qwen2.5-1.5B
      Agents: 4 (Strict, Balanced, Detailed, Lenient)
      
      <b>n=1,158</b> screened
    end note
  }

  rectangle "ELIGIBILITY" as ELIG {
    note
      <b>Vote Patterns</b>
      
      4-0 (unanimous include) 481
      3-1 (majority include) 124
      2-2 (split) 113
      1-3 (majority exclude) 227
      0-4 (unanimous exclude) 213
    end note
  }

  rectangle "ROUTING" as ROUTE {
    note
      <b>Confidence-Based Routing</b>
      
      HIGH (4-0, 0-4) → Auto-decide
      MEDIUM (3-1, 1-3) → Human review
      LOW (2-2) → Human review
    end note
  }

  rectangle "INCLUDE" as INC {
    note
      <b>Studies included</b>
      
      <i>Auto-included (high confidence)</i>
      n=481 (4-0 pattern)
      
      <i>Human-reviewed & included</i>
      n=? (awaiting review)
      
      <b>Total to include: ?</b>
    end note
  }

  rectangle "EXCLUDE" as EXCL {
    note
      <b>Studies excluded</b>
      
      <i>Auto-excluded (high confidence)</i>
      n=213 (0-4 pattern)
      
      <i>Human-reviewed & excluded</i>
      n=? (awaiting review)
    end note
  }

  rectangle "HUMAN REVIEW" as HR {
    note
      <b>Human Expert Review</b>
      n=464 papers
      
      - 124 (3-1 pattern) - likely include
      - 113 (2-2 pattern) - uncertain
      - 227 (1-3 pattern) - likely exclude
    end note
  }
}

ID --> SCR
SCR --> ELIG
ELIG --> ROUTE

ROUTE -left-> INC : Auto-INCLUDE (4-0) n=481
ROUTE -right-> EXCL : Auto-EXCLUDE (0-4) n=213
ROUTE --> HR : Human Review n=464

@enduml

---

## Summary

| Stage | n | % |
|-------|---|---|
| Identified | 1,158 | 100% |
| Screened | 1,158 | 100% |
| Auto-INCLUDE | 481 | 41.5% |
| Auto-EXCLUDE | 213 | 18.4% |
| Human Review | 464 | 40.1% |

### Final Numbers (after Human Review)

| Category | Target | Notes |
|----------|--------|-------|
| Final INCLUDE | TBD | 481 + human-reviewed include |
| Final EXCLUDE | TBD | 213 + human-reviewed exclude |