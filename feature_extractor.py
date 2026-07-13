import re
from models import Request, RequestFeatures

class FeatureExtractor:
    @staticmethod
    def extract(request: Request) -> RequestFeatures:
        prompt = request.prompt.lower()
        features = RequestFeatures()
        
        features.prompt_length = len(request.prompt.split())
        
        # Simple heuristics
        features.contains_code = bool(re.search(r'```|\b(def|class|function|var|const|let|import|from|include)\b', prompt))
        features.contains_math = bool(re.search(r'\$|\\frac|\\int|sum_|integral|theorem|proof|\b(math|equation)\b', prompt))
        features.contains_tables = bool(re.search(r'\|.*\|.*\|', prompt)) or "table" in prompt
        
        if features.contains_code:
            if "python" in prompt: features.programming_language = "python"
            elif "javascript" in prompt or "js" in prompt: features.programming_language = "javascript"
            elif "java" in prompt: features.programming_language = "java"
            elif "c++" in prompt or "cpp" in prompt: features.programming_language = "c++"
            
        features.need_json_output = "json" in prompt
        features.need_long_context = features.prompt_length > 1000 or (request.context and len(request.context.split()) > 1000)
        
        # File type detection
        features.detected_file_type = None
        if "multiple pdfs" in prompt or "research papers" in prompt or "papers" in prompt:
            features.detected_file_type = "multiple_pdfs"
        elif ".pdf" in prompt or "pdf" in prompt:
            features.detected_file_type = "pdf"
        elif ".docx" in prompt or "word doc" in prompt:
            features.detected_file_type = "docx"
        elif any(ext in prompt for ext in [".xlsx", ".csv", "excel", "spreadsheet"]):
            features.detected_file_type = "excel"
        elif any(ext in prompt for ext in [".png", ".jpg", ".jpeg", "image", "photo", "picture"]):
            features.detected_file_type = "image"
            features.contains_images = True
        elif "large codebase" in prompt or "codebase" in prompt or "repository" in prompt:
            features.detected_file_type = "codebase"
        elif "source code" in prompt or "files" in prompt:
            features.detected_file_type = "code"

        # Page / File Count Estimation
        features.document_length = 0 # page count
        page_match = re.search(r'(\d+)\s*page', prompt)
        if page_match:
            features.document_length = int(page_match.group(1))
            
        file_match = re.search(r'(\d+)\s*file', prompt)
        if file_match:
            features.number_of_files = int(file_match.group(1))
            
        # Complexity estimation (naive)
        if "expert" in prompt or "advanced" in prompt or "olympiad" in prompt or "architecture" in prompt or "distributed" in prompt:
            features.estimated_complexity = "high"
        elif "explain" in prompt or "simple" in prompt or "basic" in prompt:
            features.estimated_complexity = "low"
        else:
            features.estimated_complexity = "medium"
            
        request.features = features
        return features
