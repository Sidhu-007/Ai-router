from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ModelDefinition:
    name: str
    base_cost: float # 1M output token cost as relative proxy
    latency_score: int # 1 is lowest latency, higher is slower
    base_accuracy: float # A base accuracy heuristic, e.g. 70-100
    strengths: List[str]
    context_limit: str

# Catalog of available models from specification
MODEL_CATALOG = {
    "DeepSeek V4 Flash": ModelDefinition(
        name="DeepSeek V4 Flash",
        base_cost=0.28,
        latency_score=1,
        base_accuracy=78.0,
        strengths=["Greetings", "Translation", "Grammar", "Rewriting", "Simple summaries", "Basic Q&A", "FAQ", "Short emails", "Casual chat"],
        context_limit="1M"
    ),
    "GPT OSS 20B": ModelDefinition(
        name="GPT OSS 20B",
        base_cost=0.30,
        latency_score=2,
        base_accuracy=82.0,
        strengths=["Simple coding", "Beginner programming", "Small debugging", "Everyday reasoning", "Basic documentation"],
        context_limit="131K"
    ),
    "MiniMax M3": ModelDefinition(
        name="MiniMax M3",
        base_cost=1.20,
        latency_score=3,
        base_accuracy=86.0,
        strengths=["General conversations", "College assignments", "Medium explanations", "Brainstorming", "Writing", "Documentation", "Standard coding"],
        context_limit="512K"
    ),
    "Qwen 3.7 Plus": ModelDefinition(
        name="Qwen 3.7 Plus",
        base_cost=1.60,
        latency_score=4,
        base_accuracy=92.0,
        strengths=["Programming", "DSA", "Algorithms", "LeetCode", "Competitive Programming", "Math", "Architecture Design", "API Design", "Project Planning", "Technical Interviews", "Medium-hard reasoning"],
        context_limit="—"
    ),
    "GPT OSS 120B": ModelDefinition(
        name="GPT OSS 120B",
        base_cost=0.60, 
        latency_score=5,
        base_accuracy=94.0,
        strengths=["Writing", "Creative tasks", "Long-form content", "Medium-hard reasoning", "Better language quality"],
        context_limit="131K"
    ),
    "GLM 5.2": ModelDefinition(
        name="GLM 5.2",
        base_cost=4.40,
        latency_score=6,
        base_accuracy=95.0,
        strengths=["Research", "Long context", "Paper analysis", "Large documentation", "Scientific questions", "Medical literature", "Multi-document comparison"],
        context_limit="1M"
    ),
    "DeepSeek V4 Pro": ModelDefinition(
        name="DeepSeek V4 Pro",
        base_cost=3.48,
        latency_score=7,
        base_accuracy=98.0,
        strengths=["Very hard reasoning", "Hard debugging", "Advanced mathematics", "Olympiad problems", "Expert DSA", "Multi-step reasoning", "AI/ML architecture", "Compiler optimization", "Large codebases"],
        context_limit="1M"
    )
}

ESCALATION_ORDER = [
    "DeepSeek V4 Flash",
    "GPT OSS 20B",
    "MiniMax M3",
    "Qwen 3.7 Plus",
    "GPT OSS 120B",
    "GLM 5.2",
    "DeepSeek V4 Pro"
]

@dataclass
class RequestFeatures:
    prompt_length: int = 0
    language: str = "en"
    contains_code: bool = False
    contains_math: bool = False
    contains_images: bool = False
    contains_tables: bool = False
    programming_language: Optional[str] = None
    document_length: int = 0
    number_of_files: int = 1
    need_json_output: bool = False
    need_tool_calling: bool = False
    need_long_context: bool = False
    estimated_complexity: str = "low"

@dataclass
class Request:
    prompt: str
    context: Optional[str] = None
    features: Optional[RequestFeatures] = None
    explicit_requirements: List[str] = field(default_factory=list)

@dataclass
class ResponseEvaluation:
    confidence: float
    completeness: float
    hallucination_risk: float
    formatting_valid: bool
    json_validity: bool
    code_compiles: bool
    reasoning_quality: float

@dataclass
class RoutingHistoryEntry:
    prompt_category: str
    chosen_model: str
    latency_estimate: int
    cost_estimate: float
    confidence: float
    success: bool
    escalation_count: int
