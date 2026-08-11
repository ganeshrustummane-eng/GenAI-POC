"""
Quick DiAL API Test Script
===========================
Simple standalone script to verify your DiAL API connection.

Usage:
    python test_dial_api.py

This script will:
  1. Check if .env file exists
  2. Load DIAL_API_KEY from environment
  3. Test connection to DIAL API endpoint
  4. Send a simple test request
  5. Display the response

Exit codes:
  0 - DiAL API is working correctly
  1 - DiAL API test failed (see error message)
"""

import os
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
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

def main():
    """Main test function"""
    print_header("DiAL API Connection Test")
    
    # =========================================================================
    # Step 1: Check for .env file
    # =========================================================================
    print_info("Step 1: Checking for .env file...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print_error(".env file not found!")
        print_info("Please create .env file from .env.example:")
        print_info("  cp .env.example .env")
        print_info("Then add your DIAL_API_KEY to the .env file")
        return 1
    
    print_success(f".env file found at: {env_file.absolute()}")
    
    # =========================================================================
    # Step 2: Load environment variables
    # =========================================================================
    print_info("\nStep 2: Loading environment variables...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print_success("Environment variables loaded")
    except ImportError:
        print_error("python-dotenv not installed!")
        print_info("Install it with: pip install python-dotenv")
        return 1
    
    # =========================================================================
    # Step 3: Check DIAL_API_KEY
    # =========================================================================
    print_info("\nStep 3: Checking DIAL_API_KEY...")
    
    api_key = os.getenv("DIAL_API_KEY", "")
    if not api_key:
        print_error("DIAL_API_KEY not found in .env file!")
        print_info("Add the following to your .env file:")
        print_info("  DIAL_API_KEY=your_actual_api_key_here")
        print_info("\nGet your API key from: https://ai-proxy.lab.epam.com")
        return 1
    
    # Mask the key for display
    masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "****"
    print_success(f"DIAL_API_KEY found: {masked_key}")
    
    # =========================================================================
    # Step 4: Load configuration
    # =========================================================================
    print_info("\nStep 4: Loading DiAL configuration...")
    
    api_base = os.getenv("DIAL_API_BASE", "https://ai-proxy.lab.epam.com")
    api_version = os.getenv("DIAL_API_VERSION", "2025-04-01-preview")
    model = os.getenv("DIAL_MODEL", "gpt-4o")
    
    print_info(f"  API Base    : {api_base}")
    print_info(f"  API Version : {api_version}")
    print_info(f"  Model       : {model}")
    
    # =========================================================================
    # Step 5: Check OpenAI package
    # =========================================================================
    print_info("\nStep 5: Checking OpenAI package...")
    
    try:
        from openai import AzureOpenAI
        print_success("OpenAI package is installed")
    except ImportError:
        print_error("openai package not installed!")
        print_info("Install it with: pip install openai>=1.0.0")
        return 1
    
    # =========================================================================
    # Step 6: Test DiAL API connection
    # =========================================================================
    print_header("Testing DiAL API Connection")
    
    print_info("Sending test request to DiAL API...")
    print_info("This may take a few seconds...")
    
    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base,
        )
        
        # Send a simple test request
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: 'DiAL API is working correctly!'"
                }
            ],
            temperature=0,
            max_tokens=20,
            extra_headers={"Api-Key": api_key},
        )
        
        # Extract response
        reply = response.choices[0].message.content.strip()
        
        print_success("DiAL API connection successful!")
        print_info(f"  Response: {reply}")
        print_info(f"  Model used: {model}")
        print_info(f"  Tokens used: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
        
        # =====================================================================
        # Step 7: Final summary
        # =====================================================================
        print_header("Test Summary")
        
        print_success("All checks passed!")
        print_info("\n✅ Your DiAL API is configured correctly and working!")
        print_info("\nYou can now use AI-powered features:")
        print_info("  • AI rule mapping")
        print_info("  • Smart column matching")
        print_info("  • Semantic understanding of schema changes")
        print_info("\nNext steps:")
        print_info("  1. Run: cd src && python check_connections.py")
        print_info("  2. Test with: python validate_cli.py list-models")
        print_info("  3. Generate validation: python validate_cli.py generate --pg-table <table> --sf-table <table> --model gpt-4o")
        
        return 0
        
    except Exception as exc:
        print_error(f"DiAL API test failed: {exc}")
        
        # Provide specific troubleshooting based on error type
        error_str = str(exc).lower()
        
        print_info("\n🔍 Troubleshooting:")
        
        if "connection" in error_str or "refused" in error_str or "timeout" in error_str:
            print_warning("Network connection issue detected")
            print_info("  • Are you connected to EPAM VPN?")
            print_info("  • Check firewall settings")
            print_info("  • Try: ping ai-proxy.lab.epam.com")
            
        elif "401" in error_str or "unauthorized" in error_str:
            print_warning("Authentication issue detected")
            print_info("  • Your API key may be invalid or expired")
            print_info("  • Get a new key from: https://ai-proxy.lab.epam.com")
            print_info("  • Update DIAL_API_KEY in .env file")
            
        elif "404" in error_str or "not found" in error_str:
            print_warning("Model or endpoint not found")
            print_info("  • Check DIAL_MODEL setting in .env")
            print_info("  • Verify model name with: curl https://ai-proxy.lab.epam.com/openai/models")
            
        elif "rate limit" in error_str:
            print_warning("Rate limit exceeded")
            print_info("  • Wait a few minutes and try again")
            print_info("  • Check usage at: https://ai-proxy.lab.epam.com")
            
        else:
            print_warning("Unknown error")
            print_info("  • Check EPAM VPN connection")
            print_info("  • Verify all settings in .env file")
            print_info("  • Contact DIAL support if issue persists")
        
        print_info("\nCommon solutions:")
        print_info("  1. Connect to EPAM VPN")
        print_info("  2. Regenerate API key at: https://ai-proxy.lab.epam.com")
        print_info("  3. Update .env file with new key")
        print_info("  4. Restart terminal and try again")
        
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
