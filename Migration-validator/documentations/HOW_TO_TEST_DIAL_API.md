# How to Test Your DiAL API - Complete Guide

## Quick Answer

**Run this command to test your DiAL API:**

```powershell
python test_dial_api.py
```

**Or use the comprehensive health check:**

```powershell
cd src
python check_connections.py
```

---

## Understanding DiAL API

**DiAL** (EPAM's AI Proxy) provides access to various AI models (GPT-4, Claude, etc.) for intelligent schema mapping and validation rule generation.

### What DiAL Does for You

✅ **Smart column matching** - Handles renamed columns  
✅ **Semantic understanding** - Understands data types beyond names  
✅ **Better rule selection** - AI chooses transformation rules intelligently  
✅ **Detailed explanations** - Provides reasoning for each decision  

### What Happens Without DiAL

Without DiAL API, the system automatically falls back to **static mode**:

- ✓ Still fully functional
- ✓ Uses type-based rule matching
- ✓ Exact column name matching (case-insensitive)
- ✗ Cannot handle renamed columns
- ✗ No semantic understanding

**Bottom line:** DiAL is an enhancement, not a requirement.

---

## Testing Methods

### Method 1: Quick Test Script (Recommended for First-Time Setup)

```powershell
# Run from project root
python test_dial_api.py
```

**This script will:**
1. ✓ Check for .env file
2. ✓ Verify DIAL_API_KEY is set
3. ✓ Test connection to DIAL endpoint
4. ✓ Send a test request
5. ✓ Display detailed results

**Expected output:**
```
✓ .env file found
✓ DIAL_API_KEY found: ********
✓ DiAL API connection successful!
  Response: DiAL API is working correctly!
  Model used: gpt-4o
✅ Your DiAL API is configured correctly and working!
```

---

### Method 2: Comprehensive Health Check

```powershell
cd src
python check_connections.py
```

**Tests everything:**
- Python packages
- Environment variables
- PostgreSQL connection
- Snowflake connection
- **DiAL API connection** ← This is what you want
- Source modules

**Look for this section:**
```
==================================================================
  STEP 5 — AI / DIAL API Check (Optional)
==================================================================
  Testing DIAL endpoint: https://ai-proxy.lab.epam.com
  Model: gpt-4o
  ✓ DIAL API responded: 'OK'
  │  AI mode is ACTIVE — GPT-4o will generate validation queries
```

---

### Method 3: Test with Real Workload

```powershell
cd src
python validate_cli.py list-models
```

**Should display:**
```
Available DIAL models:
  • gpt-4o              [default]
  • gpt-4o-mini
  • gpt-4-turbo
  • anthropic.claude-3-5-sonnet-20240620-v1:0
```

**Then generate a validation plan:**
```powershell
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```

**Look for:**
```
[INFO] Using AI rule mapper (model: gpt-4o)
[INFO] AI successfully mapped 15 columns
```

---

### Method 4: Direct curl Test

```bash
curl -s "https://ai-proxy.lab.epam.com/openai/models" \
     -H "Api-Key: YOUR_API_KEY_HERE"
```

**Should return:** JSON list of available models

---

## Setup Instructions

### Step 1: Get Your API Key

1. **Connect to EPAM VPN** (required!)
2. Visit: https://ai-proxy.lab.epam.com
3. Log in with EPAM credentials
4. Navigate to API Keys section
5. Copy your personal API key

### Step 2: Configure .env File

Create/edit `.env` file in project root:

```bash
# Copy from template
cp .env.example .env
```

Add your API key:

```bash
DIAL_API_KEY=your_actual_api_key_here
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o
```

### Step 3: Verify Setup

```powershell
python test_dial_api.py
```

---

## Troubleshooting

### ❌ "DIAL_API_KEY not set"

**Problem:** Environment variable not loaded

**Solutions:**
1. Check `.env` file exists in project root
2. Verify line: `DIAL_API_KEY=your_key_here` (no spaces)
3. Restart terminal/IDE
4. Test: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DIAL_API_KEY'))"`

---

### ❌ "Connection refused" or Timeout

**Problem:** Cannot reach DIAL API endpoint

**Solutions:**
1. **Connect to EPAM VPN** ← Most common issue!
2. Check firewall settings
3. Test network: `ping ai-proxy.lab.epam.com`
4. Verify in browser: https://ai-proxy.lab.epam.com

---

### ❌ "401 Unauthorized"

**Problem:** API key invalid or expired

**Solutions:**
1. Get new API key from: https://ai-proxy.lab.epam.com
2. Check for typos in `.env` file
3. Ensure no extra spaces or quotes around key
4. Update `.env` and restart terminal

---

### ⚠️ "Falling back to static mode"

**Problem:** DiAL API unavailable or error occurred

**This is normal behavior** - system gracefully degrades:
- ✓ Validation still works
- ✓ Uses static rule matching instead
- ℹ️ AI features disabled temporarily

**Solutions:**
1. Check EPAM VPN connection
2. Verify API key
3. Wait a few minutes (API may be busy)
4. Try different model: `--model gpt-4o-mini`

---

## Success Indicators

### ✅ Your DiAL API is Working If:

1. `test_dial_api.py` shows: **"✓ DiAL API connection successful!"**
2. `check_connections.py` Step 5 shows: **"✓ DIAL API responded: 'OK'"**
3. Console output includes: **"Using AI rule mapper (model: gpt-4o)"**
4. No "falling back to static" warnings
5. Generated YAML has AI explanations

### ❌ Your DiAL API is NOT Working If:

1. Connection errors or timeouts
2. 401 Unauthorized responses
3. "DIAL_API_KEY not set" warnings
4. Always falls back to static mode
5. `list-models` command fails

---

## Available Models

| Model | Speed | Cost | Use Case |
|-------|-------|------|----------|
| **gpt-4o** | ⚡⚡ | 💰💰 | **Default** - Best accuracy |
| **gpt-4o-mini** | ⚡⚡⚡ | 💰 | Faster, simple schemas |
| **gpt-4-turbo** | ⚡⚡ | 💰💰💰 | Large contexts, complex schemas |
| **claude-3-5-sonnet** | ⚡⚡ | 💰💰 | Alternative to GPT-4 |

**Change model:**

In `.env` file:
```bash
DIAL_MODEL=gpt-4o-mini
```

Or per command:
```powershell
python validate_cli.py generate ... --model gpt-4o-mini
```

---

## Complete Testing Workflow

### First-Time Setup

```powershell
# 1. Test DiAL API
python test_dial_api.py

# 2. Comprehensive health check
cd src
python check_connections.py

# 3. List available models
python validate_cli.py list-models

# 4. Generate validation with AI
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```

### Daily Usage

```powershell
# Quick health check
cd src
python check_connections.py

# Generate validations
python validate_cli.py generate --pg-table <table> --sf-table <TABLE> --model gpt-4o
```

---

## Documentation References

📚 **Full Documentation:**

- **Complete DiAL Testing Guide:** [docs/DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md)
- **Quick Reference Card:** [docs/DIAL_API_QUICK_REFERENCE.md](docs/DIAL_API_QUICK_REFERENCE.md)
- **General Testing Guide:** [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- **Tool Overview:** [docs/TOOL_OVERVIEW.md](docs/TOOL_OVERVIEW.md)

---

## Key Takeaways

✅ **DiAL API enhances, but doesn't block** - Static mode always works  
✅ **EPAM VPN is mandatory** - Cannot connect without it  
✅ **Quick test available** - Run `python test_dial_api.py`  
✅ **Easy troubleshooting** - Check VPN, then API key  
✅ **Multiple models available** - Choose based on needs  

---

## Need Help?

**Still not working?**

1. 📖 Read: [docs/DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md)
2. 🔐 Check: EPAM VPN connection
3. 🔑 Verify: API key at https://ai-proxy.lab.epam.com
4. 💬 Ask: DIAL support at https://ai-proxy.lab.epam.com/support

**Quick support checklist:**
- [ ] EPAM VPN connected?
- [ ] API key in `.env` file?
- [ ] Terminal restarted?
- [ ] `test_dial_api.py` run successfully?

---

**Remember:** 🔐 Always connect to EPAM VPN before using DiAL API!
