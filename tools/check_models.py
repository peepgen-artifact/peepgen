from google import genai
import json
import os

def check_available_models():
    # 1. Load configuration
    config_path = "../config/gemini_config.json"
    if not os.path.exists(config_path):
        print(f"Error: configuration file not found: {config_path}")
        return

    with open(config_path, "r") as f:
        config = json.load(f)


    try:
        client = genai.Client(api_key=config["GEMINI_API_KEY"])
        print("Connecting to Google API to list models...")
        
        count = 0
        print(f"{'Model Name':<40} | {'Display Name'}")
        print("-" * 70)
        
        for m in client.models.list():
            # Filter models that support content generation
            # Note: attribute is 'supported_actions' not 'supported_generation_methods'
            if "generateContent" in m.supported_actions:
                # Remove 'models/' prefix for readability
                clean_name = m.name.replace("models/", "")
                print(f"{clean_name:<40} | {m.display_name}")
                count += 1

        
        if count == 0:
            print("\nWarning: API connection succeeded but no models supporting generateContent were found.")
            print("Please check whether your API Key has Generative Language API access.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    check_available_models()