# DiAL API Testing Guide

This guide explains how to verify your DiAL API connection and test whether it's working correctly in the Migration Validator project.

---

## Prerequisites

Before testing DiAL API, ensure you have:

1. **EPAM VPN Connection** - DiAL API requires VPN to be active
2. **DiAL API Key** - Obtain from: https://ai-proxy.lab.epam.com
3. **Python packages installed** - Run: `pip install -r requirements.txt`

---

## Quick Test Methods

### Method 1: Automated Health Check (Recommended)

The fastest way to verify your DiAL API is working:

```powershell
# From project root
cd src
python check_connections.py
```

**What to look for:**

```
==================================================================
  STEP 5 — AI / DIAL API Check (Optional)
==================================================================
  Testing DIAL endpoint: https://ai-proxy.lab.epam.com
  Model: gpt-4o
  ✓ DIAL API responded: 'OK'
  │  AI mode is ACTIVE — GPT-4o will generate validation queries
```

**If you see a warning instead:**
```
  ⚠ DIAL_API_KEY is not set.
  │  AI mode will be DISABLED — static rule matching will be used.
```
→ You need to configure your `.env` file (see Configuration section below).

---

### Method 2: Test DiAL API Directly with curl

Verify your API key works independently:

```powershell
# From PowerShell (replace YOUR_API_KEY with your actual key)
curl -s "https://ai-proxy.lab.epam.com/openai/models" -H "Api-Key: YOUR_API_KEY"
```

**Expected output:**
A JSON list of available models including:
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- `claude-3-5-sonnet`

**If you get an error:**
- `401 Unauthorized` → API key is invalid or expired
- `Connection refused` → VPN is not connected
- `Timeout` → Network/firewall issue

---

### Method 3: Test with Simple Python Script

Create a quick test script to verify programmatic access:

```python
# test_dial.py
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv("DIAL_API_KEY")
api_base = os.getenv("DIAL_API_BASE", "https://ai-proxy.lab.epam.com")
api_version = os.getenv("DIAL_API_VERSION", "2025-04-01-preview")
model = os.getenv("DIAL_MODEL", "gpt-4o")

if not api_key:
    print("❌ DIAL_API_KEY not found in .env file")
    exit(1)

try:
    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=api_base,
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say 'DiAL API is working!'"}],
        temperature=0,
        max_tokens=10,
        extra_headers={"Api-Key": api_key},
    )
    
    reply = response.choices[0].message.content
    print(f"✅ SUCCESS! DiAL API responded: {reply}")
    print(f"   Model used: {model}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print("\nTroubleshooting:")
    print("  1. Check EPAM VPN is connected")
    print("  2. Verify DIAL_API_KEY in .env file")
    print("  3. Check API key at: https://ai-proxy.lab.epam.com")
```

Run it:
```powershell
python test_dial.py
```

---

## Configuration

### Step 1: Create or Edit `.env` File

In your project root, create/edit `.env` file (copy from `.env.example`):

```bash
# ============================================================
# AI / DIAL Settings
# ============================================================
DIAL_API_KEY=your_actual_api_key_here
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o
```

**Where to get your API key:**
1. Open: https://ai-proxy.lab.epam.com
2. Log in with EPAM credentials
3. Navigate to API Keys section
4. Copy your personal API key

### Step 2: Available Models

You can change the `DIAL_MODEL` to any of these:

| Model | Description | Best For |
|-------|-------------|----------|
| `gpt-4o` | **Default** - Best accuracy | Complex schema mapping |
| `gpt-4o-mini` | Faster, lower cost | Simple migrations |
| `gpt-4-turbo` | High context window | Large schemas |
| `anthropic.claude-3-5-sonnet-20240620-v1:0` | Claude 3.5 via DIAL | Alternative AI model |
| `gemini-pro` | Google Gemini via DIAL | Experimental |

---

## Testing DiAL with Real Workload

### Test 1: List Available Models

```powershell
cd src
python validate_cli.py list-models
```

**Expected output:**
```
Available DIAL models:
  • gpt-4o              [default]
  • gpt-4o-mini
  • gpt-4-turbo
  • anthropic.claude-3-5-sonnet-20240620-v1:0
```

### Test 2: Generate Validation Plan with AI

Test DiAL by generating a validation plan for a real table:

```powershell
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```

**What to look for:**

```
[INFO] Using AI rule mapper (model: gpt-4o)
[INFO] Sending column metadata to DIAL API...
[INFO] AI successfully mapped 15 columns
[OK] Generated: validation_sql/events_validation.yaml
[OK] Generated: validation_sql/events_validation.sql
```

**If you see this instead:**
```
[INFO] DIAL_API_KEY not set — using static rule matching.
```
→ DiAL is not configured; the system falls back to static mode.

### Test 3: Compare AI vs Static Mode

Generate the same table with both modes and compare:

```powershell
# Static mode (no AI)
python validate_cli.py generate --pg-table users --sf-table USERS --mode static

# AI mode (with DiAL)
python validate_cli.py generate --pg-table users --sf-table USERS --model gpt-4o
```

**AI mode should produce:**
- Better column name matching (handles renamed columns)
- Smarter rule selection (understands semantic meaning)
- More detailed explanations in YAML comments

---

## Common Issues and Solutions

### Issue 1: "DIAL_API_KEY not set"

**Symptoms:**
```
⚠ DIAL_API_KEY is not set.
│  AI mode will be DISABLED — static rule matching will be used.
```

**Solutions:**
1. Verify `.env` file exists in project root
2. Check `DIAL_API_KEY=` line has your actual key (no spaces)
3. Restart your terminal/IDE to reload environment variables
4. Test: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DIAL_API_KEY'))"`

---

### Issue 2: "Connection refused" or Timeout

**Symptoms:**
```
❌ FAILED: HTTPSConnectionPool(host='ai-proxy.lab.epam.com', port=443): 
Max retries exceeded with url: ...
```

**Solutions:**
1. **Connect to EPAM VPN** (most common cause)
2. Check firewall settings - allow outbound HTTPS to `ai-proxy.lab.epam.com`
3. Verify network connectivity: `ping ai-proxy.lab.epam.com`
4. Try from browser: https://ai-proxy.lab.epam.com (should show API docs)

---

### Issue 3: "401 Unauthorized"

**Symptoms:**
```
❌ FAILED: Error code: 401 - {'error': {'message': 'Invalid API key', ...}}
```

**Solutions:**
1. API key expired - get a new one from https://ai-proxy.lab.epam.com
2. Key copied incorrectly (extra spaces, missing characters)
3. Using wrong environment - check `.env` not `.env.example`
4. Re-authenticate at DIAL portal and regenerate key

---

### Issue 4: AI Falls Back to Static Mode

**Symptoms:**
```
[WARN] DIAL API error: ... — falling back to static rule matching.
```

**This is by design** - the system gracefully degrades to static mode if:
- API is temporarily unavailable
- Rate limits exceeded
- Network issues
- Model is overloaded

**Solutions:**
1. Check VPN connection
2. Wait a few minutes and retry
3. Switch to a different model: `--model gpt-4o-mini`
4. Contact EPAM DIAL support if persistent

---

## Verify AI is Actually Used

To confirm AI mode is being used (not static fallback):

### Check 1: Console Output

Look for this line when running commands:
```
[INFO] Using AI rule mapper (model: gpt-4o)
```

NOT:
```
[INFO] DIAL_API_KEY not set — using static rule matching.
```

### Check 2: Generated YAML Comments

AI-generated YAMLs include detailed reasoning:

```yaml
# AI-generated validation plan using model: gpt-4o
# Explanation: Applied semantic matching to handle column renames.
# Detected that 'user_id' (PG) maps to 'USER_IDENTIFIER' (SF) despite name difference.
```

Static mode produces generic comments:
```yaml
# Generated using static rule matching
```

### Check 3: Column Mapping Quality

**AI mode** can match renamed columns:
- `user_id` → `USER_IDENTIFIER`
- `created_at` → `creation_timestamp`
- `is_active` → `active_flag`

**Static mode** only matches exact names (case-insensitive):
- `user_id` → `user_id` ✓
- `user_id` → `USER_ID` ✓
- `user_id` → `USER_IDENTIFIER` ✗ (unmatched)

---

## Testing Checklist

Before considering DiAL API "working", verify:

- [ ] `check_connections.py` shows "✓ DIAL API responded: 'OK'"
- [ ] `validate_cli.py list-models` returns model list
- [ ] Can generate validation plan with `--model gpt-4o`
- [ ] Console shows "Using AI rule mapper (model: gpt-4o)"
- [ ] Generated YAML includes AI explanation comments
- [ ] No "falling back to static" warnings
- [ ] EPAM VPN is connected and working

---

## Advanced Testing

### Test Different Models

Compare output quality across models:

```powershell
# Test with GPT-4o (default)
python validate_cli.py generate --pg-table orders --sf-table ORDERS --model gpt-4o

# Test with Claude
python validate_cli.py generate --pg-table orders --sf-table ORDERS --model anthropic.claude-3-5-sonnet-20240620-v1:0

# Test with mini (faster)
python validate_cli.py generate --pg-table orders --sf-table ORDERS --model gpt-4o-mini
```

### Monitor API Usage

Check token consumption in DIAL portal:
1. Visit: https://ai-proxy.lab.epam.com
2. Navigate to Usage/Billing section
3. View API call history and token counts

### Stress Test

Generate multiple tables to verify API reliability:

```powershell
$tables = @("users", "orders", "products", "events")
foreach ($table in $tables) {
    python validate_cli.py generate --pg-table $table --sf-table $table.ToUpper() --model gpt-4o
}
```

---

## Performance Expectations

| Operation | Expected Time | Tokens Used |
|-----------|--------------|-------------|
| Health check (`check_connections.py`) | 1-2 seconds | ~10 tokens |
| Single table generation (10 columns) | 3-5 seconds | ~500-1000 tokens |
| Large table (50+ columns) | 10-15 seconds | ~2000-3000 tokens |
| Batch generation (10 tables) | 30-60 seconds | ~5000-10000 tokens |

**Note:** First call may be slower due to API cold start.

---

## Support and Troubleshooting

If DiAL API tests continue to fail:

1. **Check EPAM VPN Status**
   - Disconnect and reconnect VPN
   - Verify VPN profile is "EPAM Corporate"

2. **Validate API Key**
   - Log in to https://ai-proxy.lab.epam.com
   - Regenerate API key
   - Update `.env` file immediately

3. **Test Network Path**
   ```powershell
   Test-NetConnection -ComputerName ai-proxy.lab.epam.com -Port 443
   ```

4. **Review Logs**
   - Check console output for detailed error messages
   - Look for SSL/TLS errors
   - Check for proxy interference

5. **Contact Support**
   - EPAM DIAL Support Portal: https://ai-proxy.lab.epam.com/support
   - Slack: #dial-support (if available)
   - Include error messages and connection test results

---

## Summary

✅ **DiAL API is working if:**
- Health check passes (step 5 in `check_connections.py`)
- `list-models` command returns available models
- Generated validation plans include AI explanations
- No fallback warnings in console output

❌ **DiAL API is NOT working if:**
- Connection timeouts or refused
- 401 Unauthorized errors
- "DIAL_API_KEY not set" warnings
- Always falls back to static mode

💡 **Remember:** The system works perfectly fine in static mode without DiAL. AI mode is an enhancement for complex schema mappings and renamed columns.
