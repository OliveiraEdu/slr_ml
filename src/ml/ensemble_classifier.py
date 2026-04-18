"""Multi-Agent Ensemble Classifier for SLR screening.

Uses multiple LLM agents with different strictness levels to classify papers,
then applies voting consensus for auto-decision.

Supports both local LLM (llama-server) and simulated fallback.
"""

import asyncio
import json
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import requests


LLAMA_SERVER_URL = "http://localhost:8081/v1"

# Chat completions endpoint (for Qwen and similar chat models)
CHAT_ENDPOINT = f"{LLAMA_SERVER_URL}/chat/completions"


class Decision(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class AgentResult:
    agent_name: str
    decision: Decision
    confidence: float  # 0-1
    reasoning: str


class EnsembleAgent:
    """Base class for screening agents."""

    SYSTEM_PROMPT = """You are an academic paper screening agent for a Systematic Literature Review on blockchain for scientific data.

TOPIC: Blockchain-anchored machine-actionable Data Management Plans (maDMPs) for scientific data provenance

IMPORTANT: Only include papers that explicitly discuss BOTH:
1. Blockchain technology AND
2. Scientific data OR research data OR data provenance

EXCLUDE if:
- Supply chain, logistics, or food tracking
- Finance, cryptocurrency, trading, DeFi
- NFTs, gaming, metaverse
- Smart contracts for business (not data)
- Non-academic sources

STRICT RULE: When in doubt, EXCLUDE. Prefer false negatives over false positives.

Respond ONLY with JSON:
{"decision": "INCLUDE" or "EXCLUDE", "confidence": 0.0-1.0, "reasoning": "one sentence"}"""

    def __init__(
        self,
        name: str,
        strictness: str,  # "strict", "balanced", "lenient"
        model: str = "claude-sonnet-4-20250514",
    ):
        self.name = name
        self.strictness = strictness
        self.model = model
        # Voting weight for confidence-weighted scoring
        self.weight = {
            "strict": 1.0,
            "balanced": 1.2,  # Neutral/balanced gets slight boost
            "lenient": 0.8,
            "detailed": 1.1,  # New detailed analyst agent
        }.get(strictness, 1.0)

    def _get_personality_prompt(self) -> str:
        prompts = {
            "strict": """
You are STRICT (High Recall): Include paper if blockchain + any of (provenance, scientific data, research data).
When uncertain about any criterion, lean toward INCLUDE.
""",
            "balanced": """
You are BALANCED: Apply strict PRISMA criteria. Include only if blockchain + (provenance OR scientific data).
Exclude if supply chain, finance, crypto, or opinion.
""",
            "lenient": """
You are LENIENT (High Precision): Only include if CLEAR evidence of:
- blockchain + scientific/research data provenance
- OR explicit maDMP implementation
Exclude if any doubt about relevance.
""",
            "detailed": """
You are DETAILED ANALYST: Focus on technical implementation.
Include if paper describes actual blockchain system for data provenance.
Exclude if conceptual only, no implementation, or non-research domain.
""",
        }
        return prompts.get(self.strictness, prompts["balanced"])

    async def classify(
        self, title: str, abstract: str, use_llama_server: bool = True
    ) -> AgentResult:
        """Classify a paper using this agent.

        Args:
            title: Paper title
            abstract: Paper abstract
            use_llama_server: If True, try local LLM first; if False, use simulation
        """

        # Build persona-specific instruction
        if self.strictness == "strict":
            instruction = "Include the paper if it mentions blockchain AND either scientific data, research data, provenance, or reproducibility. Prefer inclusion over exclusion."
        elif self.strictness == "lenient":
            instruction = "Only include if there is CLEAR evidence of blockchain for scientific data provenance or maDMPs. Exclude supply chain, finance, or non-research."
        else:
            instruction = "Apply standard PRISMA criteria: Include if blockchain + (provenance OR scientific data). Exclude if supply chain, finance, or opinion."

        # Build chat-style messages for Qwen
        messages = [
            {
                "role": "system",
                "content": f"""You are an academic paper screening agent. {instruction}

Respond ONLY with JSON: {{"decision": "INCLUDE" or "EXCLUDE", "confidence": 0.0-1.0, "reasoning": "brief reason"}}""",
            },
            {
                "role": "user",
                "content": f"""Title: {title}

Abstract: {abstract[:500] if abstract else "No abstract"}""",
            },
        ]

        # Try local llama-server with chat API
        if use_llama_server:
            try:
                response = requests.post(
                    CHAT_ENDPOINT,
                    json={
                        "model": "Qwen3.5-4B-Q4_K_M.gguf",
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 150,
                    },
                    timeout=60,
                )
                if response.status_code == 200:
                    data = response.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    return self._parse_chat_response(content, self.name)
            except Exception as e:
                print(f"LLM error: {e}, falling back to simulation")

        # Fallback: simulated response
        return self._simulate_classify(title, abstract)

    def _parse_chat_response(self, content: str, agent_name: str) -> AgentResult:
        """Parse chat API response."""
        content = content.strip()

        # Try to parse JSON
        try:
            # Find JSON in response
            json_match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                decision = Decision(data.get("decision", "UNCERTAIN"))
                confidence = float(data.get("confidence", 0.5))
                reasoning = data.get("reasoning", "")
                return AgentResult(agent_name, decision, confidence, reasoning)
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: keyword in response
        if "INCLUDE" in content.upper():
            return AgentResult(agent_name, Decision.INCLUDE, 0.7, content[:100])
        elif "EXCLUDE" in content.upper():
            return AgentResult(agent_name, Decision.EXCLUDE, 0.7, content[:100])
        else:
            return self._simulate_classify("unknown", "unknown")

    def _simulate_classify(self, title: str, abstract: str) -> AgentResult:
        """Simulate classification for prototype testing."""
        text = f"{title} {abstract}".lower()

        # Core keywords
        bc_kw = ["blockchain", "hyperledger", "fabric", "iroha", "distributed ledger"]
        prov_kw = ["provenance", "data lineage", "verification", "integrity"]
        sci_kw = [
            "scientific data",
            "research data",
            "reproducibility",
            "open science",
            "fair",
        ]

        # Exclusion keywords
        ex_kw = [
            "supply chain",
            "finance",
            "financial",
            "cryptocurrency",
            "trading",
            "opinion",
            "editorial",
            "bitcoin",
            "nft",
            "game",
            "marketing",
        ]

        # Check matches
        has_bc = any(kw in text for kw in bc_kw)
        has_prov = any(kw in text for kw in prov_kw)
        has_sci = any(kw in text for kw in sci_kw)
        has_exclude = any(kw in text for kw in ex_kw)

        # Check scientific/research context (NOT supply chain related)
        has_scientific_context = (has_bc and (has_prov or has_sci)) and not has_exclude

        # Apply strictness
        if self.strictness == "strict":
            # Strict: includes if has blockchain + any relevant term
            decision = (
                Decision.INCLUDE
                if (has_bc and (has_prov or has_sci))
                else Decision.EXCLUDE
            )
            confidence = 0.85 if decision == Decision.INCLUDE else 0.65
            reasoning = f"bc={has_bc}, prov={has_prov}, sci={has_sci}, ex={has_exclude}"

        elif self.strictness == "lenient":
            # Lenient: needs strong scientific context
            decision = Decision.INCLUDE if has_scientific_context else Decision.EXCLUDE
            confidence = 0.9 if decision == Decision.INCLUDE else 0.75
            reasoning = f"scientific_context={has_scientific_context}"

        else:  # balanced
            # Balanced: needs blockchain + at least one other relevant term
            has_relevant = has_bc and (has_prov or has_sci)
            decision = Decision.INCLUDE if has_relevant else Decision.EXCLUDE
            confidence = 0.8 if decision == Decision.INCLUDE else 0.6
            reasoning = f"relevant={has_relevant}"

        return AgentResult(
            agent_name=self.name,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
        )


class EnsembleVoter:
    """Multi-agent ensemble with weighted voting and 4 agents."""

    def __init__(self, num_agents: int = 4):
        self.agents = [
            EnsembleAgent("Strict-A", "strict"),  # High recall
            EnsembleAgent("Balanced-B", "balanced"),  # Standard PRISMA
            EnsembleAgent("Detailed-D", "detailed"),  # Technical focus
            EnsembleAgent("Lenient-C", "lenient"),  # High precision
        ][:num_agents]

    async def classify(
        self, title: str, abstract: str, require_consensus: bool = True
    ) -> dict:
        """Classify using weighted voting."""

        # Run all agents
        results = await asyncio.gather(
            *[agent.classify(title, abstract) for agent in self.agents]
        )

        # Weighted voting
        include_score = 0.0
        exclude_score = 0.0

        for r in results:
            weight = getattr(r, "weight", 1.0) if hasattr(r, "weight") else 1.0
            if r.decision == Decision.INCLUDE:
                include_score += weight
            elif r.decision == Decision.EXCLUDE:
                exclude_score += weight

        total_agents = len(self.agents)

        # Weighted vote thresholds
        if include_score >= total_agents * 0.75:  # 3/4 weighted majority
            final = Decision.INCLUDE
            confidence = 0.90
            auto = True
        elif include_score >= total_agents * 0.5:  # Simple majority
            final = Decision.INCLUDE
            confidence = 0.75
            auto = not require_consensus
        elif exclude_score >= total_agents * 0.75:
            final = Decision.EXCLUDE
            confidence = 0.90
            auto = True
        elif exclude_score >= total_agents * 0.5:
            final = Decision.EXCLUDE
            confidence = 0.75
            auto = not require_consensus
        else:
            final = Decision.UNCERTAIN
            confidence = 0.5
            auto = False

        # Simple vote count for display
        vote_counts = {Decision.INCLUDE: 0, Decision.EXCLUDE: 0, Decision.UNCERTAIN: 0}
        for r in results:
            vote_counts[r.decision] += 1

        return {
            "decision": final,
            "confidence": confidence,
            "auto_decide": auto,
            "votes": {d.value: v for d, v in vote_counts.items()},
            "weighted_scores": {"include": include_score, "exclude": exclude_score},
            "agent_results": [
                {
                    "agent": r.agent_name,
                    "decision": r.decision.value,
                    "reasoning": r.reasoning,
                }
                for r in results
            ],
        }


async def demo():
    """Demo the ensemble classifier."""

    test_papers = [
        {
            "title": "SciChain: Trustworthy Scientific Data Provenance using Blockchain",
            "abstract": """The state-of-the-art for auditing and reproducing scientific applications 
on high-performance computing systems is through a data provenance subsystem.
This paper proposes SciChain, a blockchain-based framework for ensuring 
immutable data provenance tracking for scientific research data.
We demonstrate how Hyperledger Fabric can provide tamper-proof 
provenance records for research workflows.""",
        },
        {
            "title": "Blockchain-based Supply Chain Management for Retail",
            "abstract": """We propose a blockchain-based system for tracking products 
through the retail supply chain. Using Hyperledger Fabric, we enable 
real-time tracking of inventory from warehouse to store.""",
        },
        {
            "title": "A Blockchain-Based Approach to Provenance and Reproducibility in Research",
            "abstract": """This paper describes how blockchain and distributed 
ledger technology can be used to certify research data integrity.
We present a model for capturing research process provenance 
including data, code, and experimental design.""",
        },
    ]

    voter = EnsembleVoter()

    print("=" * 60)
    print("MULTI-AGENT ENSEMBLE SCREENING DEMO")
    print("=" * 60)

    for paper in test_papers:
        result = await voter.classify(paper["title"], paper["abstract"])

        print(f"\n📄 {paper['title'][:50]}...")
        print(f"   Decision: {result['decision'].value}")
        print(f"   Confidence: {result['confidence']:.0%}")
        print(f"   Auto-decide: {result['auto_decide']}")
        print(f"   Votes: {result['votes']}")
        print(f"   Agents:")
        for ar in result["agent_results"]:
            print(f"     - {ar['agent']}: {ar['decision']}")


if __name__ == "__main__":
    asyncio.run(demo())
