"""
DiAL API - Test All Available Models
=====================================
This script tests all available DiAL models to see which ones are working.

Usage:
    python test_all_dial_models.py

This script will:
  1. Connect to DiAL API
  2. List all available models
  3. Test each model individually
  4. Report which models work and which don't
  5. Show response times for comparison

Exit codes:
  0 - At least one model is working
  1 - No models are working or connection failed
"""

import os
import sys
import time
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    """Print formatted section header"""
    print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
    print(f"{BLUE}{BOLD}{text}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 70}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"  {text}")

def print_model_name(text):
    """Print model name in cyan"""
    print(f"\n{CYAN}{BOLD}Testing: {text}{RESET}")

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        print_error(".env file not found!")
        print_info("Please create .env file from .env.example")
        return False
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print_success(f".env file loaded")
        return True
    except ImportError:
        print_error("python-dotenv not installed!")
        print_info("Install it with: pip install python-dotenv")
        return False

def get_dial_client():
    """Create and return DiAL API client"""
    api_key = os.getenv("DIAL_API_KEY", "")
    if not api_key:
        print_error("DIAL_API_KEY not found in .env file!")
        return None
    
    api_base = os.getenv("DIAL_API_BASE", "https://ai-proxy.lab.epam.com")
    api_version = os.getenv("DIAL_API_VERSION", "2025-04-01-preview")
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base,
        )
        
        masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "****"
        print_success(f"DiAL client created (Key: {masked_key})")
        
        return client, api_key
        
    except ImportError:
        print_error("openai package not installed!")
        print_info("Install it with: pip install openai>=1.0.0")
        return None

def test_model(client, api_key, model_name):
    """Test a specific model with a simple request"""
    try:
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: 'OK'"
                }
            ],
            temperature=0,
            max_tokens=10,
            extra_headers={"Api-Key": api_key},
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        reply = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'
        
        return {
            'success': True,
            'response': reply,
            'elapsed': elapsed,
            'tokens': tokens,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'response': None,
            'elapsed': None,
            'tokens': None,
            'error': str(e)
        }

def main():
    """Main test function"""
    print_header("DiAL API - Test All Available Models")
    
    # Step 1: Load environment
    print_info("Step 1: Loading environment...")
    if not load_environment():
        return 1
    
    # Step 2: Check OpenAI package
    print_info("\nStep 2: Checking OpenAI package...")
    try:
        from openai import AzureOpenAI
        print_success("OpenAI package is installed")
    except ImportError:
        print_error("openai package not installed!")
        return 1
    
    # Step 3: Create DiAL client
    print_info("\nStep 3: Creating DiAL client...")
    client_result = get_dial_client()
    if not client_result:
        return 1
    
    client, api_key = client_result
    
    # Step 4: Define models to test
    print_header("Models to Test")
    
    models_to_test = [
        ("gpt-4o", "GPT-4 Optimized - Default model"),
        ("gpt-4o-mini", "GPT-4 Optimized Mini - Faster, lower cost"),
        ("gpt-4-turbo", "GPT-4 Turbo - High context window"),
        ("gpt-4", "GPT-4 - Original"),
        ("gpt-3.5-turbo", "GPT-3.5 Turbo - Fast and efficient"),
        ("anthropic.claude-3-5-sonnet-20240620-v1:0", "Claude 3.5 Sonnet"),
        ("anthropic.claude-sonnet-5", "Claude Sonnet 5"),
        ("gemini-pro", "Google Gemini Pro"),
        ("gpt-5.6-terra-2026-07-09", "GPT-5.6 Terra (if available)"),
    ]
    
    print_info(f"Testing {len(models_to_test)} models...\n")
    for model, desc in models_to_test:
        print_info(f"  • {model} - {desc}")
    
    # Step 5: Test each model
    print_header("Testing Models")
    
    results = []
    working_models = []
    failed_models = []
    
    for model_name, description in models_to_test:
        print_model_name(f"{model_name}")
        print_info(f"Description: {description}")
        print_info("Sending test request...")
        
        result = test_model(client, api_key, model_name)
        result['model'] = model_name
        result['description'] = description
        results.append(result)
        
        if result['success']:
            print_success(f"✓ WORKING - Response: {result['response']}")
            print_info(f"  Response time: {result['elapsed']:.2f}s")
            print_info(f"  Tokens used: {result['tokens']}")
            working_models.append(model_name)
        else:
            error_msg = result['error']
            
            # Categorize error
            if '404' in error_msg or 'not found' in error_msg.lower():
                print_error(f"✗ NOT AVAILABLE - Model not found or not enabled for your key")
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                print_error(f"✗ UNAUTHORIZED - Check API key permissions")
            elif '429' in error_msg or 'rate limit' in error_msg.lower():
                print_warning(f"⚠ RATE LIMITED - Too many requests, try again later")
            elif 'timeout' in error_msg.lower():
                print_error(f"✗ TIMEOUT - Model took too long to respond")
            else:
                print_error(f"✗ FAILED - {error_msg[:100]}")
            
            failed_models.append(model_name)
    
    # Step 6: Summary
    print_header("Test Summary")
    
    print_info(f"Total models tested: {len(models_to_test)}")
    print_info(f"Working models: {len(working_models)}")
    print_info(f"Failed models: {len(failed_models)}")
    
    if working_models:
        print("\n" + GREEN + BOLD + "✓ Working Models:" + RESET)
        for model in working_models:
            result = next(r for r in results if r['model'] == model)
            print(f"{GREEN}  ✓ {model}{RESET}")
            print(f"    Response time: {result['elapsed']:.2f}s | Tokens: {result['tokens']}")
    
    if failed_models:
        print("\n" + RED + BOLD + "✗ Failed Models:" + RESET)
        for model in failed_models:
            result = next(r for r in results if r['model'] == model)
            print(f"{RED}  ✗ {model}{RESET}")
            
            error_msg = result['error']
            if '404' in error_msg or 'not found' in error_msg.lower():
                print(f"    Reason: Not available on your API key")
            elif '401' in error_msg:
                print(f"    Reason: Authorization issue")
            elif '429' in error_msg:
                print(f"    Reason: Rate limit exceeded")
            else:
                print(f"    Reason: {error_msg[:80]}...")
    
    # Step 7: Recommendations
    print_header("Recommendations")
    
    if working_models:
        print_success("You have working models! Recommendations:")
        
        # Find fastest model
        fastest = min([r for r in results if r['success']], key=lambda x: x['elapsed'])
        print_info(f"\n  Fastest model: {fastest['model']} ({fastest['elapsed']:.2f}s)")
        
        # Check for specific models
        if 'gpt-4o' in working_models:
            print_info(f"\n  ✓ gpt-4o is working - Recommended for best quality")
        if 'gpt-4o-mini' in working_models:
            print_info(f"  ✓ gpt-4o-mini is working - Recommended for speed and cost")
        if 'gpt-4-turbo' in working_models:
            print_info(f"  ✓ gpt-4-turbo is working - Recommended for large schemas")
        
        # Update .env suggestion
        print_info(f"\n💡 To use a specific model, update your .env file:")
        print_info(f"   DIAL_MODEL={working_models[0]}")
        
        # Test command
        print_info(f"\n🎯 Test with validation generation:")
        print_info(f"   cd src")
        print_info(f"   python validate_cli.py generate --pg-table events --sf-table EVENTS --model {working_models[0]}")
        
    else:
        print_error("No models are working!")
        print_info("\nPossible reasons:")
        print_info("  • EPAM VPN not connected")
        print_info("  • API key expired or invalid")
        print_info("  • Models not enabled for your API key")
        print_info("  • DiAL service temporarily unavailable")
        
        print_info("\nTroubleshooting steps:")
        print_info("  1. Verify EPAM VPN is connected")
        print_info("  2. Check API key at: https://ai-proxy.lab.epam.com")
        print_info("  3. Regenerate API key if needed")
        print_info("  4. Contact DIAL support for model access")
    
    # Step 8: Model availability notes
    print_header("Important Notes")
    
    print_info("📌 Model Availability:")
    print_info("   Not all models are available on all DIAL API keys.")
    print_info("   Your key might have access to only certain models.")
    print_info("")
    print_info("📌 Check Your Available Models:")
    print_info('   curl -s "https://ai-proxy.lab.epam.com/openai/models" \\')
    print_info(f'        -H "Api-Key: {api_key[:8]}****{api_key[-4:]}"')
    print_info("")
    print_info("📌 Request Additional Models:")
    print_info("   Contact DIAL support at: https://ai-proxy.lab.epam.com/support")
    print_info("   to request access to specific models.")
    
    return 0 if working_models else 1


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
