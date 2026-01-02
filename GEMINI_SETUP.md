# DeepSeek API Setup Guide

## ✅ Migration Complete!
Your app now uses the official **DeepSeek** cloud API.

## 🔑 Get Your API Key
1. Visit https://platform.deepseek.com/
2. Sign in and open the API Keys tab
3. Click **Generate Key** (starts with `sk-`)
4. Copy it and keep it safe

## ⚙️ Configure the App
### Option 1 – Quick test
```python
DEEPSEEK_API_KEY = "sk-your-deepseek-key"
self.chatgpt_assistant = ChatGPTAssistant(self, api_key=DEEPSEEK_API_KEY)
```

### Option 2 – Environment variable
**PowerShell**
```powershell
$env:DEEPSEEK_API_KEY = "sk-your-deepseek-key"
python main.py
```

**CMD**
```cmd
set DEEPSEEK_API_KEY=sk-your-deepseek-key
python main.py
```

**Permanent**
1. Search for *Environment Variables* in Windows
2. Add `DEEPSEEK_API_KEY` with your key

`main.py` automatically reads it:
```python
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-your-deepseek-key")
```

## 🧪 Test It
1. Run `python main.py`
2. Press any mic button
3. Speak: “What’s my streak?”

## ❓ Troubleshooting
- **401 / API key errors** → key missing/invalid
- **Quota exceeded** → check usage on dashboard (resets daily)
- **Timeout / network** → retry after checking your connection

## 🎉 Enjoy!
DeepSeek keeps your assistant fast, private, and reliable.