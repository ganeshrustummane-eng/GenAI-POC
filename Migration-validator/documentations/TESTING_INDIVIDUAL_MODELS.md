# Testing Individual DiAL Models

## Quick Commands

### Method 1: Check Which Models Are Available on Your Key
```powershell
python check_available_dial_models.py
```

This will show you **exactly which models your API key has access to**.

---

### Method 2: Test All Common Models
```powershell
python test_all_dial_models.py
```

This will:
- Test 9 common DiAL models
- Show which ones work and which don't
- Display response times for comparison
- Give recommendations based on results

---

### Method 3: Test Specific Model Manually
```powershell
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --model <MODEL_NAME>
```

Replace `<MODEL_NAME>` with one of:
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`
- `anthropic.claude-3-5-sonnet-20240620-v1:0`
- `anthropic.claude-sonnet-5`
- `gemini-pro`

---

## Understanding Your Issue

You mentioned:
> "gpt-4o-mini is working but for others [not working]"

This usually means:

### Possible Reasons:

1. **Model Not Available on Your API Key**
   - EPAM DIAL provides different model access to different users
   - Your API key might only have access to certain models
   - This is **normal** - not all keys have all models

2. **Model Name Incorrect**
   - Exact model name must match what DIAL expects
   - Case-sensitive in some cases
   - Version suffixes matter

3. **Model Rate Limits**
   - Some models have per-user rate limits
   - You might have hit the limit for specific models
   - Wait and retry

4. **Model Temporarily Unavailable**
   - DIAL services can have temporary outages for specific models
   - Check DIAL status page

---

## Diagnostic Steps

### Step 1: Check Available Models
```powershell
python check_available_dial_models.py
```

**This will show ONLY models your key can access.**

---

### Step 2: Test Each Model
```powershell
python test_all_dial_models.py
```

**Expected Output for Working Model:**
```
Testing: gpt-4o-mini
✓ WORKING - Response: OK
  Response time: 1.23s
  Tokens used: 15
```

**Expected Output for Unavailable Model:**
```
Testing: gpt-4o
✗ NOT AVAILABLE - Model not found or not enabled for your key
```

---

### Step 3: Read the Error Messages

Different errors mean different things:

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| `404 Not Found` | Model doesn't exist or not on your key | Use different model or request access |
| `401 Unauthorized` | API key issue | Regenerate API key |
| `429 Rate Limit` | Too many requests | Wait and retry |
| `Timeout` | Model taking too long | Try again or use faster model |

---

## Common Scenarios

### Scenario 1: Only `gpt-4o-mini` Works

**This is normal!** Your API key might only have access to this model.

**Solution:**
1. Use `gpt-4o-mini` for your work (it's fast and good quality)
2. OR request additional model access from DIAL support

**Update .env:**
```bash
DIAL_MODEL=gpt-4o-mini
```

---

### Scenario 2: No Models Work

**Possible causes:**
- EPAM VPN not connected
- API key expired
- Network/firewall issue

**Solution:**
1. Connect to EPAM VPN
2. Run: `python test_dial_api.py`
3. Check VPN status
4. Regenerate API key if needed

---

### Scenario 3: Models Work Intermittently

**Possible causes:**
- Rate limiting
- VPN connection drops
- DIAL service issues

**Solution:**
1. Check VPN stays connected
2. Wait between requests
3. Use `gpt-4o-mini` (usually more stable)

---

## Which Models Should You Use?

### If Only `gpt-4o-mini` Works:
✅ **Use it!** - It's:
- Fast (faster than gpt-4o)
- Cost-effective
- Good quality for schema mapping
- More stable (less rate limits)

**You don't need other models** - `gpt-4o-mini` is excellent for validation generation.

---

### If Multiple Models Work:

**Choose based on your needs:**

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `gpt-4o-mini` | Daily use, simple schemas | ⚡⚡⚡ | 💰 |
| `gpt-4o` | Complex mappings, accuracy | ⚡⚡ | 💰💰 |
| `gpt-4-turbo` | Large schemas, big contexts | ⚡⚡ | 💰💰💰 |
| `gpt-4` | Consistent quality | ⚡ | 💰💰💰 |
| `claude-3-5-sonnet` | Alternative to GPT | ⚡⚡ | 💰💰 |

---

## Testing Workflow

**Complete workflow to diagnose your issue:**

```powershell
# Step 1: Check what models are available
python check_available_dial_models.py

# Step 2: Test all common models
python test_all_dial_models.py

# Step 3: Test working model with real table
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o-mini

# Step 4: Update .env with working model
# Edit .env file:
# DIAL_MODEL=gpt-4o-mini
```

---

## Requesting Additional Models

If you need access to specific models not available on your key:

1. **Contact DIAL Support:**
   - URL: https://ai-proxy.lab.epam.com/support
   - Request access to specific models
   - Explain your use case

2. **Provide Information:**
   - Your API key name
   - Models you need
   - Reason for request
   - Estimated usage

3. **Alternative:**
   - Use what you have (`gpt-4o-mini` is great!)
   - System works perfectly with any model

---

## Important Notes

### ✅ Working with Limited Models is Normal

- Not having all models **does not limit functionality**
- `gpt-4o-mini` can do everything `gpt-4o` does
- Quality difference is minor for schema mapping
- Faster response time is often better

### ✅ Static Mode Always Works

- If NO models work, system falls back to static mode
- Static mode is rule-based (no AI)
- Still functional, just less "smart"
- Perfect for exact column name matches

### ✅ One Working Model is Enough

- You only need ONE working model
- All models can generate validations
- Pick the fastest/most reliable one
- No need to test all models each time

---

## Quick Reference

**Check available models:**
```powershell
python check_available_dial_models.py
```

**Test all models:**
```powershell
python test_all_dial_models.py
```

**Test specific model:**
```powershell
cd src
python validate_cli.py generate --pg-table <table> --sf-table <TABLE> --model <model-name>
```

**Update default model in .env:**
```bash
DIAL_MODEL=gpt-4o-mini
```

---

## Summary

**Your situation:**
- `gpt-4o-mini` works ✅
- Other models don't work ❌

**What this means:**
- Your API key has limited model access
- **This is completely normal**
- You can work perfectly fine with just `gpt-4o-mini`

**What to do:**
1. Run `python check_available_dial_models.py` to see available models
2. Run `python test_all_dial_models.py` to test all models
3. Update `.env` with: `DIAL_MODEL=gpt-4o-mini`
4. Continue using the system normally

**No action required if `gpt-4o-mini` works for you!**

---

## Need Help?

If you want additional models:
- Contact DIAL support: https://ai-proxy.lab.epam.com/support
- Or continue using `gpt-4o-mini` (recommended!)

If NO models work:
- Check EPAM VPN connection
- Run `python test_dial_api.py`
- See [DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md)
