"""Risk of bias assessment tools for SLR quality control."""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class RoBLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RoBAssessment:
    """Risk of bias assessment result."""
    paper_id: str
    selection_bias: RoBLevel
    performance_bias: RoBLevel
    detection_bias: RoBLevel
    attrition_bias: RoBLevel
    reporting_bias: RoBLevel
    overall_rob: RoBLevel
    rob2_domains: dict
    concerns: list[str]
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "selection_bias": self.selection_bias.value,
            "performance_bias": self.performance_bias.value,
            "detection_bias": self.detection_bias.value,
            "attrition_bias": self.attrition_bias.value,
            "reporting_bias": self.reporting_bias.value,
            "overall_rob": self.overall_rob.value,
            "rob2_domains": self.rob2_domains,
            "concerns": self.concerns,
            "confidence": round(self.confidence, 3),
        }


class RiskOfBiasAssessor:
    """Assess risk of bias for included studies."""
    
    ROB2_DOMAINS = [
        "bias_arising_from_randomization",
        "bias_due_to_deviations",
        "bias_due_to_missing_data",
        "bias_in_measurement_outcomes",
        "bias_in_selection_of_reported_results",
    ]
    
    ROBINS_T_DOMAINS = [
        "bias_due_to_confounders",
        "bias_in_selection_of_participants",
        "bias_in_classification_of_interventions",
        "bias_due_to_deviations_interventions",
        "bias_due_to_missing_data",
        "bias_in_measurement_outcomes",
        "bias_in_selection_of_reported_results",
    ]
    
    def assess_study(self, paper: dict, study_type: str = "nrt") -> RoBAssessment:
        """Assess risk of bias for a single study."""
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        full_text = paper.get("full_text", "") or ""
        if full_text:
            text = f"{text} {full_text.lower()}"
        
        if study_type == "rct":
            return self._assess_rob2(text, paper.get("id"))
        elif study_type == "nrt":
            return self._assess_robins_t(text, paper.get("id"))
        else:
            return self._assess_generic(text, paper.get("id"))
    
    def _assess_rob2(self, text: str, paper_id: str) -> RoBAssessment:
        """Assess RCT using RoB 2.0 tool."""
        domains = {}
        concerns = []
        
        for domain in self.ROB2_DOMAINS:
            if "randomization" in domain:
                level = self._check_randomization(text)
            elif "deviation" in domain:
                level = self._check_deviations(text)
            elif "missing" in domain or "attrition" in domain:
                level = self._check_missing_data(text)
            elif "measurement" in domain:
                level = self._check_measurement(text)
            else:
                level = self._check_reporting(text)
            
            domains[domain] = level.value
        
        selection = self._check_randomization(text)
        performance = self._check_deviations(text)
        detection = self._check_measurement(text)
        attrition = self._check_missing_data(text)
        reporting = self._check_reporting(text)
        
        levels = [selection, performance, detection, attrition, reporting]
        high_count = sum(1 for l in levels if l == RoBLevel.HIGH)
        
        if high_count >= 2:
            overall = RoBLevel.HIGH
        elif high_count == 1:
            overall = RoBLevel.MODERATE
        elif any(l == RoBLevel.MODERATE for l in levels):
            overall = RoBLevel.MODERATE
        else:
            overall = RoBLevel.LOW
        
        confidence = self._calculate_confidence(text)
        
        return RoBAssessment(
            paper_id=paper_id,
            selection_bias=selection,
            performance_bias=performance,
            detection_bias=detection,
            attrition_bias=attrition,
            reporting_bias=reporting,
            overall_rob=overall,
            rob2_domains=domains,
            concerns=concerns,
            confidence=confidence,
        )
    
    def _assess_robins_t(self, text: str, paper_id: str) -> RoBAssessment:
        """Assess non-randomized study using ROBINS-T."""
        confounders = self._check_confounders(text)
        selection = self._check_selection(text)
        classification = self._check_classification(text)
        deviations = self._check_deviations(text)
        missing = self._check_missing_data(text)
        measurement = self._check_measurement(text)
        reporting = self._check_reporting(text)
        
        levels = [confounders, selection, classification, deviations, missing, measurement, reporting]
        critical_count = sum(1 for l in levels if l == RoBLevel.CRITICAL)
        high_count = sum(1 for l in levels if l == RoBLevel.HIGH)
        
        if critical_count >= 1:
            overall = RoBLevel.CRITICAL
        elif high_count >= 2:
            overall = RoBLevel.HIGH
        elif high_count == 1:
            overall = RoBLevel.MODERATE
        else:
            overall = RoBLevel.MODERATE
        
        confidence = self._calculate_confidence(text)
        
        return RoBAssessment(
            paper_id=paper_id,
            selection_bias=selection,
            performance_bias=deviations,
            detection_bias=measurement,
            attrition_bias=missing,
            reporting_bias=reporting,
            overall_rob=overall,
            rob2_domains={"confounders": confounders.value},
            concerns=[],
            confidence=confidence,
        )
    
    def _assess_generic(self, text: str, paper_id: str) -> RoBAssessment:
        """Generic risk of bias assessment."""
        confidence = self._calculate_confidence(text)
        
        if confidence > 0.7:
            return RoBAssessment(
                paper_id=paper_id,
                selection_bias=RoBLevel.MODERATE,
                performance_bias=RoBLevel.MODERATE,
                detection_bias=RoBLevel.MODERATE,
                attrition_bias=RoBLevel.MODERATE,
                reporting_bias=RoBLevel.MODERATE,
                overall_rob=RoBLevel.MODERATE,
                rob2_domains={},
                concerns=["Generic assessment - recommend specific tool"],
                confidence=confidence,
            )
        else:
            return RoBAssessment(
                paper_id=paper_id,
                selection_bias=RoBLevel.HIGH,
                performance_bias=RoBLevel.HIGH,
                detection_bias=RoBLevel.HIGH,
                attrition_bias=RoBLevel.HIGH,
                reporting_bias=RoBLevel.HIGH,
                overall_rob=RoBLevel.HIGH,
                rob2_domains={},
                concerns=["Low confidence in assessment"],
                confidence=confidence,
            )
    
    def _check_randomization(self, text: str) -> RoBLevel:
        """Check randomization quality."""
        if any(kw in text for kw in ["randomized", "rct", "randomly assigned"]):
            if any(kw in text for kw in ["computer-generated", "random number", "stratified"]):
                return RoBLevel.LOW
            return RoBLevel.MODERATE
        return RoBLevel.HIGH
    
    def _check_deviations(self, text: str) -> RoBLevel:
        """Check protocol deviations."""
        if "blinded" in text or "masking" in text:
            return RoBLevel.LOW
        if "single-blind" in text:
            return RoBLevel.MODERATE
        return RoBLevel.HIGH
    
    def _check_missing_data(self, text: str) -> RoBLevel:
        """Check missing data handling."""
        if any(kw in text for kw in ["intention-to-treat", "itt analysis", "completer"]):
            return RoBLevel.LOW
        if "per-protocol" in text:
            return RoBLevel.MODERATE
        return RoBLevel.HIGH
    
    def _check_measurement(self, text: str) -> RoBLevel:
        """Check outcome measurement."""
        if any(kw in text for kw in ["validated", "standardized", "objective"]):
            return RoBLevel.LOW
        return RoBLevel.MODERATE
    
    def _check_reporting(self, text: str) -> RoBLevel:
        """Check reporting bias."""
        if any(kw in text for kw in ["registered", "protocol", "pre-specified"]):
            return RoBLevel.LOW
        if "prospective" in text:
            return RoBLevel.MODERATE
        return RoBLevel.HIGH
    
    def _check_confounders(self, text: str) -> RoBLevel:
        """Check confounding control."""
        if any(kw in text for kw in ["multivariate", "adjusted", "covariates"]):
            return RoBLevel.MODERATE
        return RoBLevel.HIGH
    
    def _check_selection(self, text: str) -> RoBLevel:
        """Check participant selection."""
        if any(kw in text for kw in ["consecutive", "prospective", "cohort"]):
            return RoBLevel.LOW
        return RoBLevel.MODERATE
    
    def _check_classification(self, text: str) -> RoBLevel:
        """Check intervention classification."""
        if any(kw in text for kw in ["defined", "specified", "operational"]):
            return RoBLevel.LOW
        return RoBLevel.MODERATE
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence in assessment."""
        indicators = {
            "high": ["validated", "standardized", "registered", "protocol", "objective"],
            "medium": ["described", "reported", "measured", "assessed"],
            "low": ["unclear", "not reported", "not described"],
        }
        
        high_count = sum(1 for kw in indicators["high"] if kw in text)
        medium_count = sum(1 for kw in indicators["medium"] if kw in text)
        low_count = sum(1 for kw in indicators["low"] if kw in text)
        
        total = high_count + medium_count + low_count
        if total == 0:
            return 0.3
        
        return (high_count * 1.0 + medium_count * 0.5 + low_count * 0.0) / total
