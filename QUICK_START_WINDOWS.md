# 🚀 Quick Start Guide for Windows

## ⚠️ IMPORTANT: Use Command Prompt (CMD), not PowerShell!

PowerShell has execution policy restrictions that can cause issues. **Use Command Prompt (CMD) instead.**

## Step-by-Step Setup

### 1. Open Command Prompt (CMD)
- Press `Win + R`
- Type `cmd` and press Enter
- **OR** search for "Command Prompt" in Start menu

### 2. Navigate to Backend Directory
```cmd
cd D:\Work\Projects\GenAIAgent\backend
```

### 3. Activate Virtual Environment
```cmd
venv\Scripts\activate.bat
```

**✅ You should see `(venv)` appear in your prompt!**

### 4. Install Dependencies (if not already done)
```cmd
pip install -r requirements.txt
```

### 5. Create .env File
```cmd
copy env.example .env
```

Then edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

### 6. Start Backend Server
```cmd
uvicorn main:app --reload --port 8000
```

**✅ Backend is now running at http://localhost:8000**

---

### 7. Open NEW Command Prompt Window for Frontend

In the **new** CMD window:

```cmd
cd D:\Work\Projects\GenAIAgent\codebase-agent
```

### 8. Create Frontend .env File
```cmd
copy env.local.example .env.local
```

### 9. Install Frontend Dependencies (if not done)
```cmd
npm install
```

### 10. Start Frontend Server
```cmd
npm run dev
```

**✅ Frontend is now running at http://localhost:3000**

---

## 🎯 You're Ready!

1. Open browser: `http://localhost:3000`
2. Enter a GitHub repo URL
3. Click "Analyze Repository"
4. Explore the results!

---

## ❌ Common Errors & Fixes

### Error: "uvicorn is not recognized"
**Problem:** Virtual environment is NOT activated
**Solution:** 
1. Make sure you're in the `backend` directory
2. Run `venv\Scripts\activate.bat` again
3. You MUST see `(venv)` in your prompt
4. Then run `uvicorn main:app --reload --port 8000`

### Error: "running scripts is disabled"
**Problem:** You're using PowerShell instead of CMD
**Solution:** Use Command Prompt (CMD) instead of PowerShell

### Error: "pip is not recognized"
**Problem:** Python is not installed or not in PATH
**Solution:** Install Python 3.8+ from python.org and check "Add to PATH" during installation

---

## 💡 Pro Tips

- **Always check for `(venv)` in your prompt** before running Python commands
- **Use CMD, not PowerShell** to avoid execution policy issues
- **Keep two terminal windows open** - one for backend, one for frontend
- **Check backend is running** by visiting `http://localhost:8000/health`
