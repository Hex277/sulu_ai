import os

# Əsas qovluq və məlumatların (faylların) olduğu qovluğun yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CURRENT_AI_MODE = "openai" 

if CURRENT_AI_MODE == "openai":
    LLM_BASE_URL = "https://api.openai.com/v1"
    LLM_API_KEY = "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"
    ROUTER_MODEL = "gpt-4o"
    GENERATOR_MODEL = "gpt-4o"
    
elif CURRENT_AI_MODE == "local":
    LLM_BASE_URL = "http://localhost:1234/v1" # Məsələn, LM Studio üçün
    LLM_API_KEY = "local-key" # Local üçün fərq etmir
    ROUTER_MODEL = "local-model-adin" 
    GENERATOR_MODEL = "local-model-adin"