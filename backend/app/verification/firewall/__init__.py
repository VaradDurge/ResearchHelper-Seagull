"""
Research Hallucination Firewall — No generation without retrieval; verifiable output only.
Extends (does not replace) Claim Verification Engine.
"""
from app.verification.firewall.gate import VerificationGate
from app.verification.firewall.structured_output import StructuredOutputEnforcer
from app.verification.firewall.self_check import SelfCheckValidator
from app.verification.firewall.diversity import DiversityAdjuster
from app.verification.firewall.pipeline import FirewallVerificationPipeline
from app.verification.firewall.metrics import FirewallMetrics

__all__ = [
    "VerificationGate",
    "StructuredOutputEnforcer",
    "SelfCheckValidator",
    "DiversityAdjuster",
    "FirewallVerificationPipeline",
    "FirewallMetrics",
]
