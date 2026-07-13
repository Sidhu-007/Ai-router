from models import Request, MODEL_CATALOG, ESCALATION_ORDER
import logging

class RouterEngine:
    THRESHOLDS = {
        "Easy": 85.0,
        "Medium": 90.0,
        "Hard": 94.0,
        "Expert": 97.0
    }

    @staticmethod
    def estimate_accuracy(model_name: str, domain: str, difficulty: str, request: Request) -> float:
        model = MODEL_CATALOG[model_name]
        acc = model.base_accuracy
        
        # Adjust based on strengths
        strengths_lower = [s.lower() for s in model.strengths]
        
        # Domain matches
        for strength in strengths_lower:
            if domain.lower() in strength or strength in domain.lower() or any(w in strength for w in ["programming", "research"] if w in domain.lower()):
                acc += 5.0
                break
            
        # Specific overrides based on spec
        prompt_lower = request.prompt.lower()
        if model_name == "GLM 5.2" and ("research paper" in prompt_lower or "literature" in prompt_lower or "summarize" in prompt_lower and "page" in prompt_lower):
            acc += 10.0
        
        if model_name == "DeepSeek V4 Pro" and difficulty in ["Expert", "Hard"] and ("distributed" in prompt_lower or "architecture" in prompt_lower):
            acc += 10.0
            
        if model_name == "Qwen 3.7 Plus" and ("leetcode" in prompt_lower or "graph problem" in prompt_lower):
            acc += 8.0

        if model_name == "GPT OSS 20B" and "binary search" in prompt_lower:
            acc += 5.0

        if model_name == "DeepSeek V4 Flash" and difficulty == "Easy":
            acc += 10.0

        return min(acc, 99.9) # Cap at 99.9

    @staticmethod
    def select_model(request: Request, domain: str, difficulty: str, context_req: str) -> str:
        # Allow explicit model override in the prompt
        prompt_lower = request.prompt.lower()
        for model_name in ESCALATION_ORDER:
            if model_name.lower() in prompt_lower:
                return model_name

        # Enforce file type and context specific overrides from the spec table
        if request.features:
            ftype = getattr(request.features, "detected_file_type", None)
            pages = request.features.document_length
            num_files = request.features.number_of_files
            
            if ftype == "multiple_pdfs":
                return "GLM 5.2"
            if ftype == "codebase":
                return "DeepSeek V4 Pro"
            if ftype == "pdf":
                if pages >= 20:
                    return "MiniMax M3"
                else:
                    return "Qwen 3.7 Plus"
            if ftype in ["docx", "excel", "image"]:
                return "Qwen 3.7 Plus"
            if ftype == "code":
                if num_files <= 10:
                    return "Qwen 3.7 Plus"
                else:
                    return "DeepSeek V4 Pro"

        threshold = RouterEngine.THRESHOLDS.get(difficulty, 90.0)
        
        # Spec: Never skip directly to the most expensive model unless 
        # Difficulty == Expert OR Context > 200K (Very Large) OR Research Level
        can_skip = difficulty == "Expert" or context_req == "Very Large" or domain == "Research-level Mathematics" or domain == "Research" or "highest quality" in request.explicit_requirements
        
        # For difficult research tasks, route directly to GLM 5.2
        if difficulty in ["Expert", "Hard"] and domain in ["Research", "Research-level Mathematics"]:
            return "GLM 5.2"
            
        # For difficult programming tasks, route directly to Qwen 3.7 Plus
        if difficulty in ["Expert", "Hard"] and domain in ["Programming", "Competitive Programming"]:
            return "Qwen 3.7 Plus"
            
        # For moderate tasks, route directly to MiniMax M3 (except binary search and writing tasks)
        if difficulty == "Medium":
            if "binary search" in prompt_lower:
                return "GPT OSS 20B"
            if domain == "Writing":
                return "GPT OSS 120B"
            return "MiniMax M3"

        candidates = []
        
        # Collect all eligible candidate models
        for model_name in ESCALATION_ORDER:
            # Never select the most expensive model initially if we cannot skip
            if not can_skip and model_name == "GLM 5.2":
                continue
                
            # If we can skip, we might want to prioritize specific models
            if can_skip:
                if context_req == "Very Large" and model_name not in ["GLM 5.2", "DeepSeek V4 Pro"]:
                    continue
                if difficulty == "Expert" and model_name not in ["Qwen 3.7 Plus", "GLM 5.2", "DeepSeek V4 Pro"]:
                    continue
            
            expected_acc = RouterEngine.estimate_accuracy(model_name, domain, difficulty, request)
            if expected_acc >= threshold:
                candidates.append(model_name)
                
        # Select the cheapest model among candidates, or fallback to the strongest (DeepSeek V4 Pro)
        if candidates:
            best_model = min(candidates, key=lambda m: MODEL_CATALOG[m].base_cost)
        else:
            best_model = "DeepSeek V4 Pro"
            
        return best_model
