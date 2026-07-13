from pipeline import Pipeline
from models import Request

def main():
    pipeline = Pipeline()
    
    print("Intelligent AI Model Router")
    print("Type 'exit' or 'quit' to stop.")
    
    while True:
        try:
            user_input = input("\nEnter your prompt: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            if not user_input.strip():
                continue
                
            req = Request(prompt=user_input)
            pipeline.process_request(req)
            
        except (KeyboardInterrupt, EOFError):
            break
            
    print("\n--- Final Learning Stats ---")
    print(pipeline.learning_component.get_stats())

if __name__ == "__main__":
    main()
