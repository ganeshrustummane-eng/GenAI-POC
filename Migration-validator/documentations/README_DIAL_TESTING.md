# Testing Your DiAL API - Start Here 🚀

Welcome! This guide will help you quickly test whether your DiAL API is working correctly.

---

## 🎯 Quick Start (2 Minutes)

### Step 1: Connect to EPAM VPN
**⚠️ CRITICAL:** DiAL API requires EPAM VPN connection!

### Step 2: Run the Test Script
```powershell
python test_dial_api.py
```

**Expected output:**
```
✓ .env file found
✓ DIAL_API_KEY found: ********
✓ DiAL API connection successful!
✅ Your DiAL API is configured correctly and working!
```

**If you see errors**, continue to the detailed guides below.

---

## 📚 Complete Testing Resources

### Quick References (Pick What You Need)

| Resource | Best For | Link |
|----------|----------|------|
| **Quick Test** | First-time setup, 2 min test | [`test_dial_api.py`](test_dial_api.py) |
| **Check Models** | See available models on your key | [`check_available_dial_models.py`](check_available_dial_models.py) |
| **Test All Models** | Find which models work | [`test_all_dial_models.py`](test_all_dial_models.py) |
| **Individual Models** | Test specific models, troubleshoot | [TESTING_INDIVIDUAL_MODELS.md](TESTING_INDIVIDUAL_MODELS.md) |
| **Quick Reference** | Commands, troubleshooting at-a-glance | [DIAL_API_QUICK_REFERENCE.md](docs/DIAL_API_QUICK_REFERENCE.md) |
| **Testing Checklist** | Systematic verification | [DIAL_API_TESTING_CHECKLIST.md](DIAL_API_TESTING_CHECKLIST.md) |
| **Complete Guide** | Detailed explanations, all methods | [DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md) |
| **How-To Summary** | Overview and workflows | [HOW_TO_TEST_DIAL_API.md](HOW_TO_TEST_DIAL_API.md) |

---

## 🔧 Five Ways to Test

### Method 1: Quick Test Script (Recommended)
```powershell
python test_dial_api.py
```
✅ **Best for:** Initial setup, quick verification  
⏱️ **Time:** ~30 seconds  
📋 **Tests:** API key, connectivity, basic request

---

### Method 2: Check Available Models on Your Key
```powershell
python check_available_dial_models.py
```
✅ **Best for:** Finding which models you have access to  
⏱️ **Time:** ~10 seconds  
📋 **Shows:** List of models available on your API key

---

### Method 3: Test All Models
```powershell
python test_all_dial_models.py
```
✅ **Best for:** Finding which models actually work  
⏱️ **Time:** ~2-3 minutes  
📋 **Tests:** 9 common models, shows response times

---

### Method 4: Comprehensive Health Check
```powershell
cd src
python check_connections.py
```
✅ **Best for:** Full system verification  
⏱️ **Time:** ~2-3 minutes  
📋 **Tests:** All connections, packages, DiAL API (Step 5)

---

### Method 5: Real Workload Test
```powershell
cd src
python validate_cli.py list-models
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```
✅ **Best for:** Confirming AI features work end-to-end  
⏱️ **Time:** ~5-10 seconds per command  
📋 **Tests:** Model availability, AI-powered generation

---

## ⚡ Quick Fix Guide

### ❌ "DIAL_API_KEY not set"
1. Check `.env` file exists in project root
2. Add: `DIAL_API_KEY=your_actual_key_here`
3. Get key from: https://ai-proxy.lab.epam.com
4. Restart terminal

### ❌ "Connection refused"
1. **Connect to EPAM VPN** ← 90% of issues!
2. Check: https://ai-proxy.lab.epam.com loads in browser
3. Test: `ping ai-proxy.lab.epam.com`

### ❌ "401 Unauthorized"
1. Regenerate API key at: https://ai-proxy.lab.epam.com
2. Update `.env` file
3. Restart terminal
4. Retest: `python test_dial_api.py`

---

## 📖 Detailed Documentation

### Complete Guides

1. **[DIAL API Testing Guide](docs/DIAL_API_TESTING_GUIDE.md)** - Complete reference
   - All testing methods in detail
   - Configuration instructions
   - Advanced testing scenarios
   - Performance expectations
   - Support information

2. **[How to Test DiAL API](HOW_TO_TEST_DIAL_API.md)** - Workflow guide
   - Quick answer at the top
   - Setup instructions
   - Testing workflow
   - Common issues and solutions

3. **[Testing Checklist](DIAL_API_TESTING_CHECKLIST.md)** - Systematic verification
   - Step-by-step checklist
   - Success criteria
   - Troubleshooting flowchart
   - Testing notes template

4. **[Quick Reference](docs/DIAL_API_QUICK_REFERENCE.md)** - Commands cheat sheet
   - One-page reference
   - Quick commands
   - Error messages table
   - Links and resources

---

## ✅ Success Indicators

Your DiAL API is working correctly if:

- ✓ `test_dial_api.py` shows: "✓ DiAL API connection successful!"
- ✓ `check_connections.py` Step 5 shows: "✓ DIAL API responded: 'OK'"
- ✓ Console shows: "Using AI rule mapper (model: gpt-4o)"
- ✓ No "falling back to static mode" warnings
- ✓ Generated YAML files include AI explanations

---

## 🔐 Important Notes

### VPN is Mandatory
DiAL API **requires** EPAM VPN connection. If you see connection errors:
1. Check VPN client is running
2. Verify VPN is connected (not paused)
3. Reconnect if necessary

### Static Mode Fallback
If DiAL API is unavailable, the system automatically falls back to **static mode**:
- ✅ Still fully functional
- ✅ Uses rule-based matching
- ❌ No AI-powered features
- ℹ️ This is by design - system never breaks!

### API Key Security
- ✅ Store in `.env` file (git-ignored)
- ❌ Never commit to version control
- ✅ Regenerate if compromised
- ✅ Keep it confidential

---

## 🆘 Need Help?

### Quick Support Path
1. **Try Quick Test:** `python test_dial_api.py`
2. **Check VPN:** Connect to EPAM VPN
3. **Verify Key:** https://ai-proxy.lab.epam.com
4. **Read Guide:** [DIAL_API_TESTING_GUIDE.md](docs/DIAL_API_TESTING_GUIDE.md)
5. **Contact Support:** https://ai-proxy.lab.epam.com/support

### Information to Gather
- Output from `test_dial_api.py`
- VPN connection status
- Error messages (full text)
- Python version: `python --version`

---

## 🎓 Related Documentation

- **General Testing:** [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- **Tool Overview:** [docs/TOOL_OVERVIEW.md](docs/TOOL_OVERVIEW.md)
- **Execution Guide:** [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)
- **Migration Docs:** [MIGRATION_VALIDATOR_DOCS.md](MIGRATION_VALIDATOR_DOCS.md)

---

## 🚀 Next Steps After DiAL is Working

Once your DiAL API test passes:

1. ✅ Run full health check: `cd src && python check_connections.py`
2. ✅ List available models: `python validate_cli.py list-models`
3. ✅ Generate your first validation: `python validate_cli.py generate --pg-table <table> --sf-table <TABLE> --model gpt-4o`
4. ✅ Review generated YAML files in `validation_sql/` folder
5. ✅ Run validation queries against your databases

---

## 📊 At a Glance

| Component | Status Check Command | Expected Result |
|-----------|---------------------|-----------------|
| DiAL API | `python test_dial_api.py` | ✓ DiAL API connection successful! |
| All Systems | `cd src && python check_connections.py` | ✅ ALL CHECKS PASSED |
| Models | `cd src && python validate_cli.py list-models` | List of 4+ models |
| AI Generation | `cd src && python validate_cli.py generate ...` | Using AI rule mapper |

---

## 💡 Pro Tips

1. **Always test after .env changes** - Restart terminal first
2. **VPN disconnects?** - Re-run test to verify
3. **Slow responses?** - Try `gpt-4o-mini` model
4. **First time user?** - Follow [DIAL_API_TESTING_CHECKLIST.md](DIAL_API_TESTING_CHECKLIST.md)
5. **Regular checks** - Run `python test_dial_api.py` weekly

---

## ⏱️ Time Estimates

| Task | Time Required |
|------|---------------|
| Initial setup (first time) | 10-15 minutes |
| Quick test (`test_dial_api.py`) | 30 seconds |
| Health check (`check_connections.py`) | 2-3 minutes |
| Generate validation (single table) | 5-10 seconds |
| Full documentation review | 30-45 minutes |

---

**Remember:** 🔐 Always connect to EPAM VPN before testing DiAL API!

**Quick Start Command:** `python test_dial_api.py`

---

**Questions?** Check the [Complete Testing Guide](docs/DIAL_API_TESTING_GUIDE.md) or [Quick Reference](docs/DIAL_API_QUICK_REFERENCE.md)
