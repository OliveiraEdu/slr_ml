"""Sensitivity analysis and meta-analysis support for SLR."""
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class SensitivityAnalysis:
    """Results of sensitivity analysis."""
    threshold_sensitivity: dict
    inclusion_rate_by_threshold: list[dict]
    robustness_score: float
    recommendations: list[str]
    
    def to_dict(self) -> dict:
        return {
            "threshold_sensitivity": self.threshold_sensitivity,
            "inclusion_rate_by_threshold": self.inclusion_rate_by_threshold,
            "robustness_score": round(self.robustness_score, 4),
            "recommendations": self.recommendations,
        }


@dataclass
class PublicationBiasAnalysis:
    """Publication bias assessment."""
    fail_safe_n: int
    trim_and_fill_estimates: list
    funnel_asymmetry_test: dict
    egger_test_pvalue: Optional[float]
    bias_assessment: str
    
    def to_dict(self) -> dict:
        return {
            "fail_safe_n": self.fail_safe_n,
            "trim_and_fill_estimates": self.trim_and_fill_estimates,
            "funnel_asymmetry_test": self.funnel_asymmetry_test,
            "egger_test_pvalue": self.egger_test_pvalue,
            "bias_assessment": self.bias_assessment,
            "is_concerning": self.fail_safe_n < 250 or self.egger_test_pvalue < 0.05 if self.egger_test_pvalue else self.fail_safe_n < 250,
        }


class SensitivityAnalyzer:
    """Perform sensitivity analysis on screening decisions."""
    
    def __init__(self, min_threshold: float = 0.2, max_threshold: float = 0.8, step: float = 0.05):
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.step = step
    
    def analyze_threshold_sensitivity(
        self,
        papers: list[dict],
        scores: dict[str, float],
    ) -> SensitivityAnalysis:
        """Analyze how inclusion rate changes with threshold."""
        inclusion_rates = []
        thresholds = np.arange(self.min_threshold, self.max_threshold + self.step, self.step)
        
        for threshold in thresholds:
            included = sum(1 for pid, score in scores.items() if score >= threshold)
            rate = included / len(scores) * 100 if scores else 0
            inclusion_rates.append({
                "threshold": round(threshold, 2),
                "included": included,
                "rate_percent": round(rate, 2),
            })
        
        baseline_included = sum(1 for pid, score in scores.items() if score >= 0.5)
        baseline_rate = baseline_included / len(scores) * 100 if scores else 0
        
        rate_variance = np.var([r["rate_percent"] for r in inclusion_rates])
        robustness_score = 1 / (1 + rate_variance)
        
        recommendations = []
        if robustness_score < 0.5:
            recommendations.append("Results are highly sensitive to threshold choice - recommend lower threshold")
        elif robustness_score > 0.8:
            recommendations.append("Results robust to threshold variations")
        
        threshold_at_baseline = next((r for r in inclusion_rates if r["threshold"] == 0.5), None)
        if threshold_at_baseline:
            if abs(threshold_at_baseline["rate_percent"] - baseline_rate) > 5:
                recommendations.append("Check score calibration - actual vs expected rates differ")
        
        return SensitivityAnalysis(
            threshold_sensitivity={
                "baseline_threshold": 0.5,
                "baseline_included": baseline_included,
                "baseline_rate_percent": round(baseline_rate, 2),
            },
            inclusion_rate_by_threshold=inclusion_rates,
            robustness_score=robustness_score,
            recommendations=recommendations,
        )
    
    def analyze_confidence_sensitivity(
        self,
        results: list[dict],
    ) -> dict:
        """Analyze sensitivity to confidence filtering."""
        confidence_levels = [0.1, 0.15, 0.2, 0.25, 0.3]
        
        analysis = {}
        for min_conf in confidence_levels:
            filtered = [r for r in results if r.get("confidence", 0) >= min_conf]
            included = sum(1 for r in filtered if r.get("decision") == "include")
            
            analysis[f"min_confidence_{min_conf}"] = {
                "papers_above_threshold": len(filtered),
                "included": included,
                "inclusion_rate": round(included / len(filtered) * 100, 2) if filtered else 0,
                "filtered_out": len(results) - len(filtered),
            }
        
        return analysis


class PublicationBiasAnalyzer:
    """Analyze publication bias in included studies."""
    
    def __init__(self, tolerance: float = 0.001):
        self.tolerance = tolerance
    
    def calculate_fail_safe_n(
        self,
        effect_sizes: list[float],
        alpha: float = 0.05,
    ) -> int:
        """Calculate fail-safe N (Rosenthal's method)."""
        z_values = []
        for es in effect_sizes:
            if es > self.tolerance:
                z = es / np.std(effect_sizes) if np.std(effect_sizes) > 0 else 0
                z_values.append(z)
        
        if not z_values:
            return 0
        
        sum_z = sum(z_values)
        
        k = len(effect_sizes)
        z_alpha = 1.96
        
        nfs = (sum_z / z_alpha) ** 2 - k
        
        return max(0, int(nfs))
    
    def test_funnel_asymmetry(
        self,
        effect_sizes: list[float],
        variances: list[float],
    ) -> dict:
        """Test for funnel plot asymmetry."""
        if len(effect_sizes) < 10:
            return {"test_performed": False, "reason": "Insufficient studies (< 10)"}
        
        precision = [1 / np.sqrt(v) if v > 0 else 0 for v in variances]
        
        effect_mean = np.mean(effect_sizes)
        precision_mean = np.mean(precision)
        
        residuals = [es - effect_mean for es in effect_sizes]
        weighted_residuals = [r * p for r, p in zip(residuals, precision)]
        
        slope = np.polyfit(precision, weighted_residuals, 1)[0]
        
        return {
            "test_performed": True,
            "slope": round(slope, 4),
            "asymmetry_present": abs(slope) > 0.1,
            "interpretation": "Publication bias likely" if abs(slope) > 0.1 else "No significant asymmetry detected",
        }
    
    def assess_bias(
        self,
        effect_sizes: list[float],
        citations: list[int],
        years: list[int],
    ) -> PublicationBiasAnalysis:
        """Comprehensive publication bias assessment."""
        fail_safe_n = self.calculate_fail_safe_n(effect_sizes)
        
        variances = [1.0] * len(effect_sizes)
        funnel_result = self.test_funnel_asymmetry(effect_sizes, variances)
        
        bias_indicators = {
            "fail_safe_n_adequate": fail_safe_n >= 250,
            "funnel_symmetry": not funnel_result.get("asymmetry_present", True),
            "citation_distribution": self._analyze_citations(citations),
            "year_distribution": self._analyze_years(years),
        }
        
        concerning_count = sum(1 for v in bias_indicators.values() if not v)
        
        if concerning_count >= 2:
            assessment = "High concern for publication bias"
        elif concerning_count == 1:
            assessment = "Moderate concern for publication bias"
        else:
            assessment = "Low concern for publication bias"
        
        return PublicationBiasAnalysis(
            fail_safe_n=fail_safe_n,
            trim_and_fill_estimates=[],
            funnel_asymmetry_test=funnel_result,
            egger_test_pvalue=None,
            bias_assessment=assessment,
        )
    
    def _analyze_citations(self, citations: list[int]) -> bool:
        """Check if citation distribution suggests bias."""
        if not citations:
            return True
        
        median = np.median(citations)
        highly_cited = sum(1 for c in citations if c > median * 2)
        
        return highly_cited < len(citations) * 0.3
    
    def _analyze_years(self, years: list[int]) -> bool:
        """Check if year distribution suggests bias."""
        if len(years) < 3:
            return True
        
        year_counts = {}
        for y in years:
            year_counts[y] = year_counts.get(y, 0) + 1
        
        recent_years = sum(1 for y, c in year_counts.items() if y >= max(years) - 2)
        recent_ratio = recent_years / len(years)
        
        return recent_ratio < 0.5 or recent_ratio > 0.9
