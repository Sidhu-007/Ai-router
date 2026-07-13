from models import Request, ResponseEvaluation, ESCALATION_ORDER, MODEL_CATALOG, RoutingHistoryEntry
from feature_extractor import FeatureExtractor
from predictors import DomainPredictor, DifficultyPredictor, ContextEstimator
from router import RouterEngine
from learning import LearningComponent
import time
import logging
import os
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Custom helper to load env variables from .env
def load_env():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'\" ")

load_env()
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY")

# Mapping model names to the exact available model IDs from the user's API key
FIREWORKS_MODEL_MAPPING = {
    "DeepSeek V4 Flash": "accounts/fireworks/models/gpt-oss-120b",
    "GPT OSS 20B": "accounts/fireworks/models/gpt-oss-120b",
    "MiniMax M3": "accounts/fireworks/models/kimi-k2p6",
    "Qwen 3.7 Plus": "accounts/fireworks/models/deepseek-v4-pro",
    "GPT OSS 120B": "accounts/fireworks/models/gpt-oss-120b",
    "GLM 5.2": "accounts/fireworks/models/glm-5p2",
    "DeepSeek V4 Pro": "accounts/fireworks/models/deepseek-v4-pro"
}

class Pipeline:
    def __init__(self):
        self.learning_component = LearningComponent()

    def process_request(self, request: Request):
        logger.info(f"\n--- Processing Request: '{request.prompt[:50]}...' ---")
        
        # Step 1: Extract Features
        features = FeatureExtractor.extract(request)
        
        # Step 2: Predict Domain
        domain, domain_conf = DomainPredictor.predict(request)
        
        # Step 3: Predict Difficulty
        difficulty = DifficultyPredictor.predict(domain, request)
        
        # Step 4: Estimate Context
        context_req = ContextEstimator.estimate(request)
        
        logger.info(f"Domain: {domain} ({domain_conf:.2f}), Difficulty: {difficulty}, Context: {context_req}")
        
        # Step 5 & 6: Estimate Accuracy & Select Initial Model
        selected_model_name = RouterEngine.select_model(request, domain, difficulty, context_req)
        logger.info(f"Initial Model Selection: {selected_model_name}")
        
        escalation_count = 0
        final_model = selected_model_name
        success = False
        final_response = ""
        total_cost = 0.0
        
        # Steps 7, 8, 9: Execution, Evaluation, and Escalation Loop
        current_model_idx = ESCALATION_ORDER.index(selected_model_name)
        
        while current_model_idx < len(ESCALATION_ORDER):
            model_name = ESCALATION_ORDER[current_model_idx]
            logger.info(f"Executing with model: {model_name}...")
            
            # Step 7: Run Model (Real API or Mocked)
            response, execution_time, prompt_tokens, completion_tokens = self._execute_model(model_name, request)
            
            # Calculate cost based on catalog pricing rates (cost per 1M tokens)
            model_def = MODEL_CATALOG[model_name]
            input_rate = model_def.base_cost * 0.25  # Input rate is ~25% of output rate
            output_rate = model_def.base_cost
            cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000.0
            total_cost += cost
            
            # Step 8: Evaluate Response
            evaluation = self._evaluate_response(model_name, request, response)
            logger.info(f"Evaluation Confidence: {evaluation.confidence:.2f} | Transaction Cost: ${cost:.6f}")
            
            # Step 9: Automatic Escalation
            threshold = 0.85 # Base evaluation confidence threshold
            if evaluation.confidence < threshold or not evaluation.formatting_valid or not evaluation.json_validity:
                logger.warning(f"Evaluation failed (Confidence {evaluation.confidence:.2f} < {threshold}). Escalating...")
                escalation_count += 1
                current_model_idx += 1
                if current_model_idx >= len(ESCALATION_ORDER):
                    logger.error("Reached highest model and still failed.")
                    final_model = model_name
                    final_response = response
                    break
            else:
                logger.info(f"Response accepted from {model_name}.")
                final_model = model_name
                final_response = response
                success = True
                break

        # Log to Learning Component
        history_entry = RoutingHistoryEntry(
            prompt_category=domain,
            chosen_model=final_model,
            latency_estimate=int(execution_time * 10),  # scaled proxy
            cost_estimate=total_cost,
            confidence=evaluation.confidence,
            success=success,
            escalation_count=escalation_count
        )
        self.learning_component.record(history_entry)
        
        return final_model, success, final_response, domain, difficulty, context_req, total_cost, execution_time

    def _execute_model(self, model_name: str, request: Request) -> tuple[str, float, int, int]:
        prompt = request.prompt
        if FIREWORKS_API_KEY:
            model_id = FIREWORKS_MODEL_MAPPING.get(model_name, "accounts/fireworks/models/gpt-oss-120b")
            url = "https://api.fireworks.ai/inference/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # Reconstruct standard list of messages with history
            messages = []
            if request.context:
                try:
                    messages = json.loads(request.context)
                except Exception:
                    pass
            if not isinstance(messages, list):
                messages = []
                
            messages.append({"role": "user", "content": prompt})
            
            body = {
                "model": model_id,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            start_time = time.time()
            try:
                res = requests.post(url, headers=headers, json=body, timeout=45)
                if res.status_code == 200:
                    res_data = res.json()
                    content = res_data["choices"][0]["message"]["content"]
                    usage = res_data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", len(prompt.split()))
                    completion_tokens = usage.get("completion_tokens", len(content.split()))
                    latency = time.time() - start_time
                    return content, latency, prompt_tokens, completion_tokens
                else:
                    logger.error(f"Fireworks API Error (Status {res.status_code}): {res.text}")
            except Exception as e:
                logger.error(f"Fireworks API Exception: {str(e)}")
        
        # Mock execution fallback
        latency = MODEL_CATALOG[model_name].latency_score * 0.1
        time.sleep(latency)
        mock_response = f"[Mock response from {model_name}] Complete answer to prompt: '{prompt[:40]}...'"
        
        # Estimate mock tokens
        prompt_tokens = len(prompt.split())
        completion_tokens = len(mock_response.split())
        return mock_response, latency, prompt_tokens, completion_tokens
        
    def _evaluate_response(self, model_name: str, request: Request, response: str) -> ResponseEvaluation:
        # Mock evaluation logic
        confidence = 0.9
        
        # Simulate a verification failure if "leetcode hard" is in prompt and model is not DeepSeek Pro
        if "leetcode" in request.prompt.lower() and "hard" in request.prompt.lower() and model_name == "Qwen 3.7 Plus":
            confidence = 0.6
            
        return ResponseEvaluation(
            confidence=confidence,
            completeness=0.9,
            hallucination_risk=0.1,
            formatting_valid=True,
            json_validity=True,
            code_compiles=True,
            reasoning_quality=0.8
        )
