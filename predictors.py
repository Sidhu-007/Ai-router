from models import Request

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "to", "for", "in", 
    "on", "at", "by", "from", "with", "about", "against", "between", "into", 
    "through", "during", "before", "after", "above", "below", "up", "down", "out", 
    "off", "over", "under", "again", "further", "once", "here", "there", "when", 
    "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", 
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", 
    "now", "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", 
    "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", 
    "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", 
    "their", "theirs", "themselves", "what", "which", "who", "whom", "this", 
    "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", 
    "being", "have", "has", "had", "having", "do", "does", "did", "doing",
    "of", "do", "does", "did", "doing", "would", "should", "could", "ought", "must"
}

def normalize_word(word: str) -> str:
    word = word.lower()
    # Lemmatization mapping for common variations
    if word in ["maths", "math", "mathematics", "mathematical", "arithmetic"]:
        return "mathematics"
    if word in ["analyse", "analysis", "analyzing", "analyzes", "analyzer", "analyzed"]:
        return "analyze"
    if word in ["programming", "programmer", "program", "programs", "code", "coding"]:
        return "program"
    if word in ["debugging", "debugged", "debugs", "bug", "bugs", "error", "errors", "issue"]:
        return "debug"
    if word in ["images", "photo", "picture", "pictures", "diagram", "screenshot", "png", "jpg", "jpeg"]:
        return "image"
    if word in ["documents", "doc", "docs", "pdf", "pdfs", "paper", "literature"]:
        return "document"
    if word in ["translation", "translating", "translated", "translates"]:
        return "translate"
    if word in ["distributed", "consensuses", "consensus", "replication", "sharding", "database"]:
        return "system"
    return word

DOMAIN_TEMPLATES = {
    "General Chat": [
        "hi hello how are you casual chat tell me a joke general conversation greetings speak talk say"
    ],
    "Programming": [
        "write python code javascript function c++ class debug program compiler syntax error shell script scripting git sql command html css rust java go"
    ],
    "Debugging": [
        "debug exception stacktrace trace runtime compile error fix memory leak crash segmentation fault logs trace back inspect bug warning"
    ],
    "Mathematics": [
        "mathematical mathematics math theorem proof prove calculus equation integration algebra logic geometry formal proofs statistics probability linear"
    ],
    "Competitive Programming": [
        "leetcode dynamic programming binary search graph algorithm dsa tree sorting complexity competitive programming greedy recursion queue stack"
    ],
    "Research": [
        "summarize research paper literature review scientific journal page summary research thesis publication citation abstract pdf"
    ],
    "Translation": [
        "translate english to french spanish how do you say in other language text translation translation bilingual translator multilingual speak"
    ],
    "Writing": [
        "write essay story article blog post creative paragraph copy editing grammar corrector composition author draft rewrite novel"
    ],
    "Business": [
        "business plan marketing strategy revenue projection pitch deck finance slide sales memo report pitch startup excel sheet forecast"
    ],
    "Medical": [
        "medical diagnosis symptoms treatment health disease clinical patient prescription drug biology doctor hospital surgery anatomy vaccine"
    ],
    "Legal": [
        "legal contract compliance litigation lawyer clause terms agreement regulation law statute case patent trademark"
    ],
    "Science": [
        "physics chemistry biology astronomy geology molecule atom chemical element scientific experiment laboratory energy force cells"
    ],
    "Education": [
        "teach lesson syllabus student textbook homework lecture university school grade course professor learning tutorial study academy"
    ],
    "System Design": [
        "distributed architecture design database replication consensus load balancer microservices system scaling design gateway broker queue kafka redis"
    ],
    "AI / ML": [
        "neural network machine learning deep learning weights transformers prompt engineering dataset training model weights inference llama gpt pytorch tensor"
    ],
    "Image Understanding": [
        "image photo picture diagram graphic screenshot visual vision look png jpg jpeg camera view inspect visual object detection ocr description"
    ],
    "Document Analysis": [
        "pdf document read extract text file csv excel table parse metadata scanning layout table extraction scanned form document parser"
    ],
    "Large Context": [
        "large context limit long document book 300 page many pages multiple files codebase analysis folder directory project repo massive"
    ],
    "Tool Use": [
        "tool calling function call api request query database search executor run command execute web browsing action agent prompt run shell plugin"
    ]
}

DIFFICULTY_TEMPLATES = {
    "Easy": [
        "hello hi simple rewrite casual chat basic greetings short answer translate word easy explain basic definition what is"
    ],
    "Medium": [
        "write function code medium dsa assignment api documentation project design outline basic parsing medium state prove theorem"
    ],
    "Hard": [
        "graph algorithms dynamic programming compiler optimization research paper summary large architecture design math proof optimize hard"
    ],
    "Expert": [
        "formal verification proof distributed systems replication consensus research-level mathematics compiler theory validation ai architecture logic expert"
    ]
}

def get_words(text: str) -> set[str]:
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
    words = cleaned.split()
    return {normalize_word(w) for w in words if w not in STOP_WORDS}

def calculate_score(prompt_words: set[str], prompt_text: str, template: str) -> float:
    template_words = get_words(template)
    if not template_words or not prompt_words:
        return 0.0
    
    # Jaccard similarity
    intersection = prompt_words.intersection(template_words)
    union = prompt_words.union(template_words)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Phrase containment bonus
    containment = 0.0
    if template in prompt_text:
        containment = 0.5
        
    return jaccard + containment

class DomainPredictor:
    @staticmethod
    def predict(request: Request) -> tuple[str, float]:
        prompt_text = request.prompt.lower()
        
        # --- Layer 1: High-Precision Substring Checks ---
        if "leetcode" in prompt_text or "binary search" in prompt_text or "competitive programming" in prompt_text:
            return "Competitive Programming", 0.95
        if "distributed database" in prompt_text or "consensus" in prompt_text or "replication" in prompt_text or "system design" in prompt_text:
            return "System Design", 0.95
        if "formal verification" in prompt_text or "coq proof" in prompt_text or "tla+" in prompt_text:
            return "Mathematics", 0.95
        if "state and prove" in prompt_text or "theorem" in prompt_text or "prove the" in prompt_text:
            return "Mathematics", 0.95
        if "research paper" in prompt_text or "scientific journal" in prompt_text or "literature review" in prompt_text:
            return "Research", 0.95
        if "translate from" in prompt_text or "translate to" in prompt_text or "how do you say" in prompt_text:
            return "Translation", 0.95
        if "pdf" in prompt_text or "read this document" in prompt_text:
            return "Document Analysis", 0.95
        if "explain from image" in prompt_text or "visual inspection" in prompt_text:
            return "Image Understanding", 0.95
            
        # --- Layer 2: Semantic Jaccard Similarity Fallback ---
        prompt_words = get_words(prompt_text)
        best_domain = "General Chat"
        max_score = 0.0
        
        for domain, templates in DOMAIN_TEMPLATES.items():
            for template in templates:
                score = calculate_score(prompt_words, prompt_text, template)
                if score > max_score:
                    max_score = score
                    best_domain = domain
                    
        # Fallbacks if Jaccard finds nothing strong
        if max_score <= 0.05:
            if "algorithm" in prompt_text or "dsa" in prompt_text or "sorting" in prompt_text:
                return "Competitive Programming", 0.9
            if "design" in prompt_text or "architecture" in prompt_text or "distributed" in prompt_text:
                return "System Design", 0.85
            if "research" in prompt_text or "paper" in prompt_text or "literature" in prompt_text:
                return "Research", 0.9
            if "translate" in prompt_text:
                return "Translation", 0.95
            if "pdf" in prompt_text or "csv" in prompt_text or "excel" in prompt_text or "document" in prompt_text:
                return "Document Analysis", 0.85
            if "image" in prompt_text or "photo" in prompt_text:
                return "Image Understanding", 0.85
            
        confidence = min(0.6 + max_score * 0.4, 0.95)
        return best_domain, confidence

class DifficultyPredictor:
    @staticmethod
    def predict(domain: str, request: Request) -> str:
        prompt_text = request.prompt.lower()
        
        # --- Layer 1: High-Precision Substring Checks ---
        if "expert" in prompt_text or "formal verification" in prompt_text or "consensus" in prompt_text or "multi-agent system" in prompt_text:
            return "Expert"
        if "hard" in prompt_text or "optimize" in prompt_text or "graph algorithm" in prompt_text or "dynamic programming" in prompt_text:
            return "Hard"
        if "simple rewrite" in prompt_text or "basic translation" in prompt_text or "hello" in prompt_text:
            return "Easy"
            
        # --- Layer 2: Semantic Jaccard Similarity Fallback ---
        prompt_words = get_words(prompt_text)
        best_difficulty = None
        max_score = 0.0
        
        for difficulty, templates in DIFFICULTY_TEMPLATES.items():
            for template in templates:
                score = calculate_score(prompt_words, prompt_text, template)
                if score > max_score:
                    max_score = score
                    best_difficulty = difficulty
                    
        # Fall back if no high-confidence template match
        if not best_difficulty or max_score <= 0.05:
            if domain in ["System Design", "Research"]:
                return "Hard"
            if domain in ["Programming", "Mathematics", "Competitive Programming"]:
                if "simple" in prompt_text or "basic" in prompt_text or "easy" in prompt_text:
                    return "Easy"
                return "Medium"
            if domain in ["General Chat", "Translation"]:
                return "Easy"
            return "Medium"
            
        return best_difficulty

class ContextEstimator:
    @staticmethod
    def estimate(request: Request) -> str:
        prompt = request.prompt.lower()
        length = request.features.prompt_length if request.features else len(request.prompt.split())
        if request.context:
            length += len(request.context.split())
            
        if "page" in prompt and any(str(i) in prompt for i in range(100, 1000)):
            return "Very Large"
            
        if "large codebase" in prompt:
            return "Large"
            
        if length < 500:
            return "Small"
        elif length < 2000:
            return "Medium"
        elif length < 10000:
            return "Large"
        else:
            return "Very Large"
