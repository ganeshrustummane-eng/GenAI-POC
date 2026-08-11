# DiAL API Quick Reference Card

## 🚀 Quick Test Commands

```powershell
# Method 1: Automated health check (Recommended)
cd src
python check_connections.py

# Method 2: Standalone test script
python test_dial_api.py

# Method 3: List available models
cd src
python validate_cli.py list-models

# Method 4: Test with real workload
cd src
python validate_cli.py generate --pg-table events --sf-table EVENTS --model gpt-4o
```

---

## 📋 Required Environment Variables

Add these to your `.env` file:

```bash
DIAL_API_KEY=your_actual_api_key_here
DIAL_API_BASE=https://ai-proxy.lab.epam.com
DIAL_API_VERSION=2025-04-01-preview
DIAL_MODEL=gpt-4o
```

**Get your API key:** https://ai-proxy.lab.epam.com

---

## ✅ Success Indicators

Your DiAL API is working if you see:

- ✓ Health check shows: **"DIAL API responded: 'OK'"**
- ✓ Console output: **"Using AI rule mapper (model: gpt-4o)"**
- ✓ No "falling back to static" warnings
- ✓ Generated YAML includes AI explanation comments

---

## ❌ Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `DIAL_API_KEY not set` | Missing/empty key in .env | Add key to .env file |
| `Connection refused` | VPN not connected | **Connect to EPAM VPN** |
| `401 Unauthorized` | Invalid/expired key | Get new key from DIAL portal |
| `Timeout` | Network/firewall issue | Check VPN, firewall settings |
| `Falling back to static` | API unavailable | Check VPN, wait & retry |

---

## 🔧 Quick Troubleshooting

**Problem:** DiAL API not working  
**Solution checklist:**

1. ✓ Connect to **EPAM VPN**
2. ✓ Verify API key from: https://ai-proxy.lab.epam.com
3. ✓ Update `DIAL_API_KEY` in `.env` file (no spaces)
4. ✓ Restart terminal/IDE
5. ✓ Run: `python test_dial_api.py`

---

## 🎯 Available Models

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| `gpt-4o` | Medium | Medium | **Default - Best quality** |
| `gpt-4o-mini` | Fast | Low | Simple schemas |
| `gpt-4-turbo` | Medium | High | Large contexts |
| `anthropic.claude-3-5-sonnet-20240620-v1:0` | Medium | Medium | Alternative to GPT |

Change model in `.env`:
```bash
DIAL_MODEL=gpt-4o-mini
```

Or override per command:
```powershell
python validate_cli.py generate ... --model gpt-4o-mini
```

---

## 🧪 Test curl Command

```bash
curl -s "https://ai-proxy.lab.epam.com/openai/models" -H "Api-Key: YOUR_API_KEY"
```

Should return JSON list of available models.

---

## 📊 What DiAL AI Provides

✅ **With DiAL (AI Mode):**
- Smart column name matching (handles renames)
- Semantic understanding of data types
- Better rule selection
- Detailed explanations
- Handles ambiguous mappings

❌ **Without DiAL (Static Mode):**
- Exact name matching only (case-insensitive)
- Type-based rules only
- No rename detection
- Basic explanations
- Unmatched columns skipped

**Note:** Static mode still works perfectly fine - AI is an enhancement, not a requirement.

---

## 🔗 Important Links

- **DIAL Portal:** https://ai-proxy.lab.epam.com
- **API Documentation:** https://ai-proxy.lab.epam.com/docs
- **Get API Key:** https://ai-proxy.lab.epam.com (login with EPAM credentials)
- **EPAM VPN:** Required for all DIAL API access

---

## 💡 Pro Tips

1. **First time setup?** Run in this order:
   ```powershell
   python test_dial_api.py          # Test API
   cd src
   python check_connections.py       # Full health check
   python validate_cli.py list-models  # Verify models
   ```

2. **Slow responses?** Try `gpt-4o-mini` for faster results

3. **Token limits?** Generate tables one at a time instead of batch

4. **AI not helping?** For exact column names, static mode is equally good

5. **Debugging?** Check console output for "Using AI rule mapper" message

---

## 📱 Quick Support

**Still not working?**

1. Check this doc: `docs/DIAL_API_TESTING_GUIDE.md`
2. Check VPN: Most common issue!
3. Regenerate API key at DIAL portal
4. Contact DIAL support: https://ai-proxy.lab.epam.com/support

---

## 🎓 Learn More

- **Full Testing Guide:** `docs/DIAL_API_TESTING_GUIDE.md`
- **General Testing:** `docs/TESTING_GUIDE.md`
- **Tool Overview:** `docs/TOOL_OVERVIEW.md`
- **Execution Guide:** `EXECUTION_GUIDE.md`

---

**Remember:** 🔐 Always connect to EPAM VPN before testing DiAL API!
