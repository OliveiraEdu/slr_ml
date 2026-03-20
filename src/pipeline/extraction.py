"""Data extraction for included studies."""
import yaml
from collections import Counter
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.models.schemas import (
    Paper, ExtractionData, QualityRating, QualityAssessment, MMATScore
)


class ExtractionExtractor:
    """Extract study characteristics from papers using config-based keyword matching."""

    def __init__(self, config_path: str = "config/extraction.yaml"):
        self.config = self._load_config(config_path)
        self.research_focus_keywords = self.config.get("extraction", {}).get("research_focus_keywords", {})
        self.blockchain_platforms = self.config.get("extraction", {}).get("blockchain_platforms", [])
        self.storage_integration = self.config.get("extraction", {}).get("storage_integration", [])
        self.permission_models = self.config.get("extraction", {}).get("permission_models", [])
        self.evaluation_methods = self.config.get("extraction", {}).get("evaluation_methods", [])

    def _load_config(self, config_path: str) -> dict:
        """Load extraction config from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def extract(self, papers: list[Paper]) -> list[ExtractionData]:
        """Extract data from included papers."""
        extracted = []
        for idx, paper in enumerate(papers, start=1):
            data = self._extract_from_paper(paper, idx)
            extracted.append(data)
        return extracted

    def _extract_from_paper(self, paper: Paper, index: int) -> ExtractionData:
        """Extract data from a single paper."""
        text = f"{paper.title} {paper.abstract or ''} {' '.join(paper.keywords)}".lower()
        raw_text = f"{paper.title} {paper.abstract or ''}"

        research_focus = self._extract_research_focus(text)
        blockchain_platform = self._extract_blockchain_platform(text)
        storage = self._extract_storage_integration(text)
        permission = self._extract_permission_model(text)
        evaluation = self._extract_evaluation_method(text)
        provenance_model = self._extract_provenance_model(text)
        madmp_standard = self._extract_madmp_standard(text)
        approach_type = self._extract_approach_type(text)
        fair_compliance = self._extract_fair_compliance(text)
        
        consensus = self._extract_consensus_mechanism(text)
        provenance_approach = self._extract_provenance_approach(text)

        return ExtractionData(
            study_id=f"REV{index:03d}",
            paper_id=paper.id,
            citation=self._generate_citation(paper),
            research_focus=research_focus,
            approach_type=approach_type,
            system_description=None,
            blockchain_platform=blockchain_platform,
            blockchain_type=self._extract_blockchain_type(text),
            consensus_mechanism=consensus,
            smart_contract_language=self._extract_smart_contract_language(text),
            madmp_standard=madmp_standard,
            metadata_schema=None,
            linked_data_support="linked data" in text or "rdf" in text,
            fair_principles_compliance=fair_compliance,
            provenance_model=provenance_model,
            provenance_approach=provenance_approach,
            verification_mechanism=self._extract_verification_mechanism(text),
            storage_integration=storage,
            data_partitioning=self._extract_data_partitioning(text),
            data_encryption="encrypt" in text,
            permission_model=permission,
            access_control_mechanism=self._extract_access_control(text),
            evaluation_method=evaluation,
            performance_metrics=None,
            scalability_assessment=self._extract_scalability(text),
            benchmarks_reported="benchmark" in text or "performance" in text,
            key_findings=None,
            contributions=None,
            novel_aspects=None,
            limitations=None,
            future_work=None,
            methodological_quality=None,
            extraction_date=datetime.now().isoformat(),
        )

    def _generate_citation(self, paper: Paper) -> str:
        """Generate citation string."""
        authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown"
        year = f" ({paper.year})" if paper.year else ""
        journal = f". {paper.journal}" if paper.journal else ""
        return f"{authors}{year}{journal}"

    def _extract_research_focus(self, text: str) -> str:
        """Extract research focus from text."""
        scores = {}
        for focus, keywords in self.research_focus_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            scores[focus] = score

        if scores.get("provenance", 0) > 0 and scores.get("blockchain", 0) > 0:
            return "Provenance + Blockchain"
        elif scores.get("provenance", 0) > 0:
            return "Provenance"
        elif scores.get("blockchain", 0) > 0:
            return "Blockchain"
        elif scores.get("madmp", 0) > 0 or "data management plan" in text:
            return "Data Management"
        return "Other"

    def _extract_approach_type(self, text: str) -> str:
        """Extract approach type."""
        if "framework" in text or "architecture" in text:
            return "Framework"
        elif "survey" in text or "systematic review" in text:
            return "Survey"
        elif "protocol" in text:
            return "Protocol"
        elif "tool" in text or "system" in text:
            return "Technical Implementation"
        elif "case study" in text:
            return "Case Study"
        return "Not specified"

    def _extract_blockchain_platform(self, text: str) -> str:
        """Extract blockchain platform from text."""
        platforms_found = []
        text_lower = text.lower()

        platform_keywords = {
            "Hyperledger Fabric": ["hyperledger fabric", "hlf"],
            "Hyperledger Indy": ["hyperledger indy"],
            "Hyperledger": ["hyperledger"],
            "Ethereum": ["ethereum", "ether"],
            "Corda": ["corda", "r3 corda"],
            "R3 Corda": ["r3 corda", "corda"],
            "Solana": ["solana"],
            "Polygon": ["polygon", "matic"],
            "IPFS": ["ipfs", "interplanetary"],
            "Cardano": ["cardano"],
            "Polkadot": ["polkadot"],
            "Multi-chain": ["multi-chain", "cross-chain"],
        }

        for platform, keywords in platform_keywords.items():
            if any(kw in text_lower for kw in keywords):
                if platform not in platforms_found:
                    platforms_found.append(platform)

        if not platforms_found:
            return "Not specified"
        return "; ".join(platforms_found)

    def _extract_blockchain_type(self, text: str) -> str:
        """Extract blockchain type (public/private/consortium)."""
        text_lower = text.lower()
        
        if "consortium" in text_lower:
            return "Consortium"
        elif "private" in text_lower:
            return "Private"
        elif "public" in text_lower:
            return "Public"
        return "Not specified"

    def _extract_consensus_mechanism(self, text: str) -> str:
        """Extract consensus mechanism."""
        text_lower = text.lower()
        
        mechanisms = {
            "Proof of Work": ["proof of work", "pow"],
            "Proof of Stake": ["proof of stake", "pos"],
            "PBFT": ["pbft", "practical byzantine", "byzantine fault tolerance"],
            "Raft": ["raft consensus"],
            "Proof of Authority": ["proof of authority", "poa"],
        }
        
        for mech, keywords in mechanisms.items():
            if any(kw in text_lower for kw in keywords):
                return mech
        return "Not specified"

    def _extract_smart_contract_language(self, text: str) -> str:
        """Extract smart contract language."""
        text_lower = text.lower()
        
        languages = {
            "Solidity": ["solidity"],
            "Go": ["golang", "go language"],
            "Rust": ["rust"],
            "Java": ["java"],
            "TypeScript": ["typescript"],
        }
        
        for lang, keywords in languages.items():
            if any(kw in text_lower for kw in keywords):
                return lang
        return "Not specified"

    def _extract_storage_integration(self, text: str) -> str:
        """Extract storage integration type."""
        text_lower = text.lower()

        if "ipfs" in text_lower and "blockchain" in text_lower:
            return "IPFS + Blockchain"
        elif "ipfs" in text_lower:
            return "IPFS"
        elif "swarm" in text_lower:
            return "Swarm"
        elif "external database" in text_lower or "external db" in text_lower:
            return "External Database"
        elif "on-chain" in text_lower or "onchain" in text_lower:
            return "On-chain"
        elif "off-chain" in text_lower or "offchain" in text_lower:
            return "Off-chain"
        elif "hybrid" in text_lower:
            return "Hybrid"
        return "Not specified"

    def _extract_permission_model(self, text: str) -> str:
        """Extract permission model."""
        text_lower = text.lower()

        if "permissioned" in text_lower and "permissionless" in text_lower:
            return "Hybrid"
        elif "permissioned" in text_lower:
            return "Permissioned"
        elif "permissionless" in text_lower:
            return "Permissionless"
        return "Not specified"

    def _extract_evaluation_method(self, text: str) -> str:
        """Extract evaluation method."""
        text_lower = text.lower()

        if "experiment" in text_lower or "empirical" in text_lower:
            return "Experimental"
        elif "case study" in text_lower:
            return "Case Study"
        elif "simulation" in text_lower:
            return "Simulation"
        elif "benchmark" in text_lower or "performance evaluation" in text_lower:
            return "Benchmark"
        elif "theoretical" in text_lower:
            return "Theoretical"
        return "Not specified"

    def _extract_provenance_model(self, text: str) -> str:
        """Extract provenance model."""
        text_lower = text.lower()
        
        models = {
            "PROV-O": ["prov-o", "prov ontology"],
            "DCAT": ["dcat", "data catalog"],
            "OPM": ["opm", "open provenance model"],
            "PROV": ["prov-", "w3c prov"],
        }
        
        for model, keywords in models.items():
            if any(kw in text_lower for kw in keywords):
                return model
        return "Not specified"

    def _extract_provenance_approach(self, text: str) -> str:
        """Extract provenance tracking approach."""
        text_lower = text.lower()
        
        if "on-chain" in text_lower or "onchain" in text_lower:
            return "On-chain"
        elif "off-chain" in text_lower or "offchain" in text_lower:
            return "Off-chain"
        elif "hybrid" in text_lower:
            return "Hybrid"
        return "Not specified"

    def _extract_verification_mechanism(self, text: str) -> str:
        """Extract verification mechanism."""
        text_lower = text.lower()
        
        if "cryptographic" in text_lower or "signature" in text_lower:
            return "Cryptographic"
        elif "smart contract" in text_lower:
            return "Smart Contract"
        elif "consensus" in text_lower:
            return "Consensus-based"
        return "Not specified"

    def _extract_fair_compliance(self, text: str) -> str:
        """Extract FAIR principles compliance."""
        text_lower = text.lower()
        
        fair_keywords = ["findable", "accessible", "interoperable", "reusable"]
        found = sum(1 for kw in fair_keywords if kw in text_lower)
        
        if found >= 3:
            return "Fully Compliant"
        elif found >= 1:
            return "Partially Compliant"
        elif "fair" in text_lower:
            return "Mentioned"
        return "Not Assessed"

    def _extract_madmp_standard(self, text: str) -> str:
        """Extract DMP standard."""
        text_lower = text.lower()
        
        standards = {
            "DMP Common Standard": ["dmp common standard", "dmpcommon"],
            "RO-Crate": ["ro-crate", "ro crate"],
            "Dublin Core": ["dublin core"],
            "DCAT": ["dcat"],
            "DataCite": ["datacite"],
        }
        
        for standard, keywords in standards.items():
            if any(kw in text_lower for kw in keywords):
                return standard
        return "Not specified"

    def _extract_data_partitioning(self, text: str) -> str:
        """Extract data partitioning strategy."""
        text_lower = text.lower()
        
        if "sharding" in text_lower:
            return "Sharding"
        elif "partitioning" in text_lower:
            return "Partitioning"
        elif "fragmentation" in text_lower:
            return "Fragmentation"
        return "Not specified"

    def _extract_access_control(self, text: str) -> str:
        """Extract access control mechanism."""
        text_lower = text.lower()
        
        if "rbac" in text_lower or "role-based" in text_lower:
            return "RBAC"
        elif "abac" in text_lower or "attribute-based" in text_lower:
            return "ABAC"
        elif "acl" in text_lower or "access control list" in text_lower:
            return "ACL"
        return "Not specified"

    def _extract_scalability(self, text: str) -> str:
        """Extract scalability assessment."""
        text_lower = text.lower()
        
        if "high scalability" in text_lower or "highly scalable" in text_lower:
            return "High"
        elif "scalable" in text_lower:
            return "Medium"
        elif "limited scalability" in text_lower or "not scalable" in text_lower:
            return "Low"
        return "Not Assessed"


class QualityAssessor:
    """Quality assessment using MMAT criteria from config."""

    def __init__(self, config_path: str = "config/extraction.yaml"):
        self.config = self._load_config(config_path)
        self.mmat_criteria = self.config.get("quality_assessment", {}).get("mmat_criteria", {})
        self.rating_thresholds = self.config.get("quality_assessment", {}).get("rating_thresholds", {})

    def _load_config(self, config_path: str) -> dict:
        """Load extraction config from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def assess(self, papers: list[Paper]) -> list[QualityAssessment]:
        """Assess quality for included papers."""
        assessments = []
        for paper in papers:
            assessment = self._assess_paper(paper)
            assessments.append(assessment)
        return assessments

    def _assess_paper(self, paper: Paper) -> QualityAssessment:
        """Assess quality of a single paper."""
        text = f"{paper.title} {paper.abstract or ''}".lower()

        mmat = MMATScore()
        yes_count = 0

        for criterion, keywords in self.mmat_criteria.items():
            found = any(kw.lower() in text for kw in keywords)
            setattr(mmat, criterion, "Yes" if found else "Can't tell")
            if found:
                yes_count += 1

        overall_score = yes_count / 5.0 if self.mmat_criteria else 0

        rating = self._calculate_rating(overall_score)

        return QualityAssessment(
            paper_id=paper.id,
            mmat_score=mmat,
            rating=rating,
            overall_score=overall_score,
            notes=None,
        )

    def _calculate_rating(self, score: float) -> QualityRating:
        """Calculate quality rating based on score."""
        thresholds = self.rating_thresholds
        if score >= thresholds.get("excellent", 0.8):
            return QualityRating.EXCELLENT
        elif score >= thresholds.get("good", 0.6):
            return QualityRating.GOOD
        elif score >= thresholds.get("acceptable", 0.4):
            return QualityRating.ACCEPTABLE
        elif score >= thresholds.get("poor", 0.2):
            return QualityRating.POOR
        else:
            return QualityRating.VERY_POOR


class SynthesisGenerator:
    """Generate synthesis from extracted data."""

    def __init__(self):
        pass

    def synthesize(
        self,
        extraction_data: list[ExtractionData],
        quality_data: list[QualityAssessment],
    ) -> dict:
        """Generate synthesis statistics and themes from extracted data."""
        
        synthesis = {
            "overview": self._generate_overview(extraction_data),
            "blockchain_analysis": self._analyze_blockchains(extraction_data),
            "platform_distribution": self._analyze_platforms(extraction_data),
            "approach_types": self._analyze_approaches(extraction_data),
            "evaluation_analysis": self._analyze_evaluations(extraction_data),
            "quality_overview": self._summarize_quality(quality_data),
            "research_gaps": self._identify_gaps(extraction_data),
            "trends": self._identify_trends(extraction_data),
        }
        
        return synthesis

    def _generate_overview(self, data: list[ExtractionData]) -> dict:
        """Generate overview statistics."""
        return {
            "total_studies": len(data),
            "with_blockchain": sum(1 for d in data if d.blockchain_platform and d.blockchain_platform != "Not specified"),
            "with_provenance": sum(1 for d in data if d.provenance_model and d.provenance_model != "Not specified"),
            "with_madmp": sum(1 for d in data if d.madmp_standard and d.madmp_standard != "Not specified"),
        }

    def _analyze_blockchains(self, data: list[ExtractionData]) -> dict:
        """Analyze blockchain characteristics."""
        platforms = Counter()
        blockchain_types = Counter()
        consensus = Counter()
        
        for d in data:
            if d.blockchain_platform and d.blockchain_platform != "Not specified":
                for p in d.blockchain_platform.split(";"):
                    platforms[p.strip()] += 1
            if d.blockchain_type:
                blockchain_types[d.blockchain_type] += 1
            if d.consensus_mechanism:
                consensus[d.consensus_mechanism] += 1
        
        return {
            "platforms": dict(platforms.most_common(10)),
            "blockchain_types": dict(blockchain_types),
            "consensus_mechanisms": dict(consensus),
        }

    def _analyze_platforms(self, data: list[ExtractionData]) -> dict:
        """Analyze technology platforms."""
        platforms = {
            "hyperledger_fabric": 0,
            "ethereum": 0,
            "ipfs": 0,
            "other": 0,
        }
        
        for d in data:
            if not d.blockchain_platform or d.blockchain_platform == "Not specified":
                continue
            platform_lower = d.blockchain_platform.lower()
            if "hyperledger" in platform_lower:
                platforms["hyperledger_fabric"] += 1
            elif "ethereum" in platform_lower:
                platforms["ethereum"] += 1
            elif "ipfs" in platform_lower:
                platforms["ipfs"] += 1
            else:
                platforms["other"] += 1
        
        return platforms

    def _analyze_approaches(self, data: list[ExtractionData]) -> dict:
        """Analyze research approaches."""
        approaches = Counter()
        for d in data:
            if d.approach_type:
                approaches[d.approach_type] += 1
        return dict(approaches)

    def _analyze_evaluations(self, data: list[ExtractionData]) -> dict:
        """Analyze evaluation methods."""
        methods = Counter()
        scalability = Counter()
        
        for d in data:
            if d.evaluation_method:
                methods[d.evaluation_method] += 1
            if d.scalability_assessment:
                scalability[d.scalability_assessment] += 1
        
        return {
            "methods": dict(methods),
            "scalability_assessments": dict(scalability),
            "with_benchmarks": sum(1 for d in data if d.benchmarks_reported),
        }

    def _summarize_quality(self, data: list[QualityAssessment]) -> dict:
        """Summarize quality assessment."""
        if not data:
            return {"message": "No quality data available"}
        
        ratings = Counter(d.rating.value if d.rating else "unknown" for d in data)
        scores = [d.overall_score for d in data if d.overall_score is not None]
        
        return {
            "rating_distribution": dict(ratings),
            "mean_score": sum(scores) / len(scores) if scores else 0,
            "total_assessed": len(data),
        }

    def _identify_gaps(self, data: list[ExtractionData]) -> list[str]:
        """Identify research gaps."""
        gaps = []
        
        no_provenance = sum(1 for d in data if not d.provenance_model or d.provenance_model == "Not specified")
        if no_provenance > len(data) * 0.3:
            gaps.append("Limited provenance model specification")
        
        no_madmp = sum(1 for d in data if not d.madmp_standard or d.madmp_standard == "Not specified")
        if no_madmp > len(data) * 0.5:
            gaps.append("Limited maDMP standard adoption")
        
        no_evaluation = sum(1 for d in data if not d.evaluation_method or d.evaluation_method == "Not specified")
        if no_evaluation > len(data) * 0.3:
            gaps.append("Limited evaluation methodology reporting")
        
        no_consensus = sum(1 for d in data if not d.consensus_mechanism or d.consensus_mechanism == "Not specified")
        if no_consensus > len(data) * 0.5:
            gaps.append("Limited consensus mechanism specification")
        
        return gaps

    def _identify_trends(self, data: list[ExtractionData]) -> list[str]:
        """Identify trends."""
        trends = []
        
        hyperledger_count = sum(1 for d in data if d.blockchain_platform and "hyperledger" in d.blockchain_platform.lower())
        if hyperledger_count > len(data) * 0.3:
            trends.append("Hyperledger Fabric is the dominant platform")
        
        ipfs_count = sum(1 for d in data if d.storage_integration and "ipfs" in d.storage_integration.lower())
        if ipfs_count > len(data) * 0.2:
            trends.append("IPFS is commonly used for storage integration")
        
        prov_o_count = sum(1 for d in data if d.provenance_model and "prov" in d.provenance_model.lower())
        if prov_o_count > len(data) * 0.1:
            trends.append("PROV-O gaining adoption for provenance modeling")
        
        return trends
