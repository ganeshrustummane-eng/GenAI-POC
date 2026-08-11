# DiAL API Testing Checklist

Use this checklist to systematically verify your DiAL API setup.

---

## 🔍 Pre-Testing Checklist

Before testing DiAL API, ensure:

- [ ] **Python 3.9+ installed** - Check: `python --version`
- [ ] **Virtual environment activated** - `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)
- [ ] **Dependencies installed** - Run: `pip install -r requirements.txt`
- [ ] **EPAM VPN connected** - ⚠️ CRITICAL - DiAL requires VPN!
- [ ] **.env file exists** - Should be in project root
- [ ] **DIAL_API_KEY obtained** - From https://ai-proxy.lab.epam.com

---

## ✅ Configuration Checklist

Verify your `.env` file contains:

```bash
# Check each line exists and has correct values
- [ ] DIAL_API_KEY=<your-actual-key-here>        # No spaces, quotes, or placeholder text
- [ ] DIAL_API_BASE=https://ai-proxy.lab.epam.com  # Correct URL
- [ ] DIAL_API_VERSION=2025-04-01-preview         # Correct version
- [ ] DIAL_MODEL=gpt-4o                           # Valid model name
```

**Quick verification command:**
```powershell
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', 'SET' if os.getenv('DIAL_API_KEY') else 'NOT SET')"
```

- [ ] Command outputs: `API Key: SET`

---

## 🧪 Testing Progression Checklist

### Level 1: Basic Connectivity

**Run:** `python test_dial_api.py`

Expected results:
- [ ] ✓ .env file found
- [ ] ✓ Environment variables loaded
- [ ] ✓ DIAL_API_KEY found (masked display)
- [ ] ✓ OpenAI package is installed
- [ ] ✓ DiAL API connection successful
- [ ] Response includes: "DiAL API is working correctly!"
- [ ] No error messages

**If any fail:** See [Troubleshooting Section](#troubleshooting)

---

### Level 2: Comprehensive Health Check

**Run:** `cd src && python check_connections.py`

Expected results:
- [ ] Step 1: ✓ All Python packages found
- [ ] Step 2: ✓ All environment variables set
- [ ] Step 3: ✓ PostgreSQL connection (if testing DB)
- [ ] Step 4: ✓ Snowflake connection (if testing DB)
- [ ] **Step 5: ✓ DIAL API responded: 'OK'** ← Primary check
- [ ] Step 6: ✓ All source modules import successfully
- [ ] Summary shows: "✅ ALL CHECKS PASSED"

---

### Level 3: Model Availability

**Run:** `cd src && python validate_cli.py list-models`

Expected results:
- [ ] Command completes without errors
- [ ] List includes: `gpt-4o [default]`
- [ ] List includes: `gpt-4o-mini`
- [ ] List includes: `gpt-4-turbo`
- [ ] List includes at least 3-4 models
- [ ] No "DIAL_API_KEY not set" warning

---

### Level 4: Real Workload Test

**Run:** `cd src && python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o`

(Replace `events` with an actual table in your database)

Expected results:
- [ ] Console shows: `Using AI rule mapper (model: gpt-4o)`
- [ ] No "falling back to static" warnings
- [ ] Files generated: `validation_sql/events_validation.yaml`
- [ ] Files generated: `validation_sql/events_validation.sql`
- [ ] YAML contains: `# AI-generated validation plan using model: gpt-4o`
- [ ] YAML contains: `# Explanation:` section with AI reasoning
- [ ] Column mappings present in YAML
- [ ] No errors during generation

---

## 🔧 Troubleshooting Checklist

If tests fail, work through this checklist:

### Issue: "DIAL_API_KEY not set"

- [ ] `.env` file exists in project root (not in `src/` folder)
- [ ] Line in `.env` reads: `DIAL_API_KEY=actual_key_here` (no spaces)
- [ ] No quotes around the key value
- [ ] Not using `.env.example` (copy to `.env` first)
- [ ] Terminal/IDE restarted after editing `.env`
- [ ] Test command shows key is set:
  ```powershell
  python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DIAL_API_KEY')[:8] if os.getenv('DIAL_API_KEY') else 'NOT SET')"
  ```

---

### Issue: "Connection refused" or Timeout

- [ ] **EPAM VPN is connected** (check VPN client)
- [ ] VPN connection is active (not paused/disconnected)
- [ ] Can access: https://ai-proxy.lab.epam.com in browser
- [ ] Firewall allows outbound HTTPS to `ai-proxy.lab.epam.com`
- [ ] No proxy blocking the connection
- [ ] Network is stable (not public WiFi with restrictions)
- [ ] Test ping: `ping ai-proxy.lab.epam.com`

---

### Issue: "401 Unauthorized"

- [ ] API key is valid (not expired)
- [ ] API key copied correctly (no extra spaces/characters)
- [ ] Using correct API key (check DIAL portal)
- [ ] Regenerate key at: https://ai-proxy.lab.epam.com
- [ ] Update `.env` with new key
- [ ] Restart terminal
- [ ] Test with curl:
  ```bash
  curl -s "https://ai-proxy.lab.epam.com/openai/models" -H "Api-Key: YOUR_KEY"
  ```

---

### Issue: "Falling back to static mode"

This is a warning, not a fatal error. The system still works.

Check:
- [ ] Previous tests (Level 1-3) all passed
- [ ] VPN still connected (may have disconnected)
- [ ] API not rate-limited (wait 5 minutes, retry)
- [ ] Try different model: `--model gpt-4o-mini`
- [ ] API endpoint is operational (check DIAL status page)

---

## 📊 Success Criteria

Your DiAL API is **fully working** if:

### Minimal Success (Level 1-2)
- [x] `test_dial_api.py` passes
- [x] `check_connections.py` Step 5 passes
- [x] No connection errors

### Full Success (Level 1-4)
- [x] All Level 1-2 checks pass
- [x] `list-models` returns model list
- [x] Can generate validation with AI
- [x] Console shows "Using AI rule mapper"
- [x] Generated YAML has AI explanations

---

## 🎯 Quick Test Commands

Copy-paste these to test quickly:

```powershell
# Test 1: Basic connectivity
python test_dial_api.py

# Test 2: Health check
cd src && python check_connections.py

# Test 3: List models
cd src && python validate_cli.py list-models

# Test 4: Generate with AI (replace table names)
cd src && python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o

# Back to root
cd ..
```

---

## 📝 Testing Notes Template

Use this template to document your testing:

```
Date: ___________
Tester: ___________
Environment: ___________

Pre-Testing:
[ ] VPN Connected: YES / NO
[ ] .env configured: YES / NO
[ ] Dependencies installed: YES / NO

Level 1 - Basic Connectivity:
[ ] test_dial_api.py: PASS / FAIL
    Error (if any): ___________

Level 2 - Health Check:
[ ] check_connections.py: PASS / FAIL
    Step 5 (DIAL): PASS / FAIL
    Error (if any): ___________

Level 3 - Models:
[ ] list-models command: PASS / FAIL
    Models listed: ___________

Level 4 - Real Workload:
[ ] AI generation: PASS / FAIL
    Model used: ___________
    Tables tested: ___________
    Files generated: YES / NO

Issues Encountered:
___________________________________________

Resolution Steps:
___________________________________________

Final Status: ✅ WORKING / ❌ NOT WORKING / ⚠️ PARTIALLY WORKING
```

---

## 🆘 Support Resources

If you've worked through this checklist and DiAL still isn't working:

**Documentation:**
- [ ] Read: [docs/DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md) (complete guide)
- [ ] Read: [docs/DIAL_API_QUICK_REFERENCE.md](docs/DIAL_API_QUICK_REFERENCE.md) (quick ref)
- [ ] Read: [HOW_TO_TEST_DIAL_API.md](HOW_TO_TEST_DIAL_API.md) (summary)

**Support Channels:**
- [ ] DIAL Portal: https://ai-proxy.lab.epam.com
- [ ] DIAL Support: https://ai-proxy.lab.epam.com/support
- [ ] Check DIAL status page for outages

**Information to Provide:**
- [ ] Output from `test_dial_api.py`
- [ ] Output from `check_connections.py`
- [ ] VPN connection status
- [ ] Error messages (full text)
- [ ] Operating system and Python version

---

## 📅 Regular Maintenance Checklist

Perform these checks periodically:

**Weekly:**
- [ ] Verify VPN connection still works
- [ ] Test DiAL API: `python test_dial_api.py`
- [ ] Check API key hasn't expired

**Monthly:**
- [ ] Review API usage/quotas on DIAL portal
- [ ] Update packages: `pip install --upgrade openai`
- [ ] Run full health check

**After Issues:**
- [ ] Regenerate API key if compromised
- [ ] Update `.env` with new key
- [ ] Re-run all tests

---

## ✨ Best Practices

- ✅ **Always check VPN first** - Most common issue
- ✅ **Keep API key secure** - Never commit to git
- ✅ **Test after .env changes** - Restart terminal
- ✅ **Document issues** - Help future debugging
- ✅ **Use test script regularly** - Quick validation

---

**Last Updated:** 2024
**Document Version:** 1.0
**Maintained By:** CodeMie Developer

---

**Quick Start:** Run `python test_dial_api.py` and follow the output!
