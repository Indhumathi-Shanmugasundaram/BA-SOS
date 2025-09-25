import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

load_dotenv()
# Build absolute path to .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path=env_path)

def configure_gemini():
    """Configure Gemini AI with API key"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    genai.configure(api_key=api_key)
    
    # Use a more reliable model - try flash first as it has higher quota
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        # Fallback to other available models
        return genai.GenerativeModel('gemini-1.5-pro-002')

def get_gemini_response(input_prompt, model=None, max_retries=3):
    """Get response from Gemini AI with retry logic and rate limiting"""
    if model is None:
        model = configure_gemini()
    
    for attempt in range(max_retries):
        try:
            # Add a small delay to avoid rate limiting
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            response = model.generate_content(input_prompt)
            return response.text
            
        except Exception as e:
            error_str = str(e)
            print(f"Attempt {attempt + 1} failed: {error_str}")
            
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = 60 * (attempt + 1)  # Wait 60, 120, 180 seconds
                    print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("Rate limit exceeded. Please try again later or upgrade your API plan.")
            
            elif "404" in error_str or "not found" in error_str.lower():
                # Try different models
                alternative_models = [
                    'gemini-1.5-flash-latest',
                    'gemini-1.5-flash-002', 
                    'gemini-1.5-pro-latest',
                    'gemini-2.0-flash-exp'
                ]
                
                for alt_model in alternative_models:
                    try:
                        print(f"Trying alternative model: {alt_model}")
                        model = genai.GenerativeModel(alt_model)
                        response = model.generate_content(input_prompt)
                        return response.text
                    except:
                        continue
                
                raise Exception("No available models found. Please check your API access.")
            
            elif attempt == max_retries - 1:
                raise e
    
    raise Exception("Max retries exceeded")

def list_available_models():
    """List all available models for debugging"""
    try:
        models = genai.list_models()
        available_models = []
        for model in models:
            if 'generateContent' in [method.name for method in model.supported_generation_methods]:
                available_models.append(model.name)
        return available_models
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

if __name__ == "__main__":
    try:
        print("Available models that support generateContent:")
        models = list_available_models()
        for model in models[:10]:  # Show first 10
            print(f"  - {model}")
        
        print("\nTesting model configuration...")
        model = configure_gemini()
        print(f"Using model: {model._model_name}")
        
        response = get_gemini_response("Say hello briefly!")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if you have exceeded your API quota")
        print("2. Verify your API key is valid")
        print("3. Try again after some time if you hit rate limits")
        print("4. Consider upgrading your API plan for higher limits")