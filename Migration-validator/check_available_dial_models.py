"""
Check Available DiAL Models
============================
This script queries DiAL API to see which models are available on your API key.

Usage:
    python check_available_dial_models.py

This script will:
  1. Connect to DiAL API
  2. Fetch list of available models
  3. Display model details (name, ID, limits)
  4. Show which models you can use

Exit codes:
  0 - Successfully fetched models list
  1 - Failed to connect or fetch models
"""

import os
import sys
import json
from pathlib import Path

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
    print(f"{BLUE}{BOLD}{text}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    print(f"  {text}")

def main():
    print_header("Check Available DiAL Models")
    
    # Load environment
    print_info("Loading environment variables...")
    env_file = Path(".env")
    if not env_file.exists():
        print_error(".env file not found!")
        return 1
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print_success(".env file loaded")
    except ImportError:
        print_error("python-dotenv not installed!")
        return 1
    
    # Get API key
    api_key = os.getenv("DIAL_API_KEY", "")
    if not api_key:
        print_error("DIAL_API_KEY not found in .env file!")
        return 1
    
    masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "****"
    print_success(f"API Key found: {masked_key}")
    
    # Get API base
    api_base = os.getenv("DIAL_API_BASE", "https://ai-proxy.lab.epam.com")
    print_info(f"API Base: {api_base}")
    
    # Fetch models using OpenAI client
    print_info("\nFetching available models from DiAL API...")
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("DIAL_API_VERSION", "2025-04-01-preview"),
            azure_endpoint=api_base,
        )
        
        # List models
        models = client.models.list()
        
        print_success(f"Successfully fetched models list!")
        
        # Display models
        print_header("Available Models on Your API Key")
        
        if not models.data:
            print_warning("No models found. This might be an issue with your API key.")
            return 1
        
        print_info(f"Total models available: {len(models.data)}\n")
        
        # Group models by category
        gpt_models = []
        claude_models = []
        gemini_models = []
        other_models = []
        
        for model in models.data:
            model_id = model.id
            if 'gpt' in model_id.lower():
                gpt_models.append(model)
            elif 'claude' in model_id.lower() or 'anthropic' in model_id.lower():
                claude_models.append(model)
            elif 'gemini' in model_id.lower():
                gemini_models.append(model)
            else:
                other_models.append(model)
        
        # Display GPT models
        if gpt_models:
            print(f"{CYAN}{BOLD}OpenAI GPT Models:{RESET}")
            for model in gpt_models:
                print(f"{GREEN}  ✓ {model.id}{RESET}")
                if hasattr(model, 'created'):
                    print(f"    Created: {model.created}")
                if hasattr(model, 'owned_by'):
                    print(f"    Owner: {model.owned_by}")
            print()
        
        # Display Claude models
        if claude_models:
            print(f"{CYAN}{BOLD}Anthropic Claude Models:{RESET}")
            for model in claude_models:
                print(f"{GREEN}  ✓ {model.id}{RESET}")
                if hasattr(model, 'created'):
                    print(f"    Created: {model.created}")
                if hasattr(model, 'owned_by'):
                    print(f"    Owner: {model.owned_by}")
            print()
        
        # Display Gemini models
        if gemini_models:
            print(f"{CYAN}{BOLD}Google Gemini Models:{RESET}")
            for model in gemini_models:
                print(f"{GREEN}  ✓ {model.id}{RESET}")
                if hasattr(model, 'created'):
                    print(f"    Created: {model.created}")
                if hasattr(model, 'owned_by'):
                    print(f"    Owner: {model.owned_by}")
            print()
        
        # Display other models
        if other_models:
            print(f"{CYAN}{BOLD}Other Models:{RESET}")
            for model in other_models:
                print(f"{GREEN}  ✓ {model.id}{RESET}")
                if hasattr(model, 'created'):
                    print(f"    Created: {model.created}")
                if hasattr(model, 'owned_by'):
                    print(f"    Owner: {model.owned_by}")
            print()
        
        # Recommendations
        print_header("Recommendations")
        
        # Check for specific models
        model_ids = [m.id for m in models.data]
        
        recommended = []
        if 'gpt-4o' in model_ids:
            recommended.append('gpt-4o')
            print_success("gpt-4o is available - Best for accuracy")
        
        if 'gpt-4o-mini' in model_ids:
            recommended.append('gpt-4o-mini')
            print_success("gpt-4o-mini is available - Best for speed and cost")
        
        if 'gpt-4-turbo' in model_ids:
            recommended.append('gpt-4-turbo')
            print_success("gpt-4-turbo is available - Best for large contexts")
        
        if not recommended:
            print_warning("None of the recommended models found.")
            print_info("You can still use any of the available models above.")
        
        print_info("\n💡 To use a specific model, update .env file:")
        if recommended:
            print_info(f"   DIAL_MODEL={recommended[0]}")
        else:
            print_info(f"   DIAL_MODEL={models.data[0].id}")
        
        print_info("\n🧪 Test all available models:")
        print_info("   python test_all_dial_models.py")
        
        return 0
        
    except ImportError:
        print_error("openai package not installed!")
        print_info("Install it with: pip install openai>=1.0.0")
        return 1
    
    except Exception as e:
        print_error(f"Failed to fetch models: {e}")
        
        error_str = str(e).lower()
        print_info("\n🔍 Troubleshooting:")
        
        if "connection" in error_str or "refused" in error_str:
            print_warning("Network connection issue")
            print_info("  • Check EPAM VPN connection")
            print_info("  • Verify firewall settings")
        elif "401" in error_str or "unauthorized" in error_str:
            print_warning("Authentication issue")
            print_info("  • API key may be invalid or expired")
            print_info("  • Get new key from: https://ai-proxy.lab.epam.com")
        else:
            print_warning("Unknown error")
            print_info("  • Verify VPN connection")
            print_info("  • Check API key validity")
        
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
