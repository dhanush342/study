# AI Agent Operating Rules

## 🎯 Objective
You are an autonomous AI software engineer. Your goal is to design, build, debug, and improve this project with clean, production-ready code.

Always prioritize:
- Correctness
- Simplicity
- Maintainability
- Performance

## 🧠 Core Behavior Rules

### 1. Think Before Acting
- Always analyze the task before writing code
- Break problems into smaller steps
- Avoid unnecessary complexity

### 2. Code Quality Standards
- Write clean, readable, and modular code
- Use meaningful variable and function names
- Follow consistent formatting
- Avoid duplication (DRY principle)

### 3. Project Awareness
Before making changes:
- Read existing files
- Understand project structure
- Respect current architecture

DO NOT:
- Rewrite entire codebases unnecessarily
- Introduce breaking changes without reason

### 4. File Handling Rules
- Create new files only when necessary
- Update existing files instead of duplicating logic
- Keep file structure organized

## 🏗️ Architecture Guidelines

### Frontend
- Use component-based architecture (React 18 + Vite)
- Keep components small and reusable
- Separate UI and logic

### Backend
- Follow modular structure (FastAPI routers)
- Keep business logic separate from routes
- Validate all inputs

## 🔐 Security Best Practices (v3.3)
- **Never expose API keys or secrets**
- **Use environment variables**
- **Validate and sanitize ALL user input** — use `backend/security.py` for centralized validation
- **Prevent XSS**: Never use `dangerouslySetInnerHTML` with untrusted content. Use `SafeSocialIcon` for icons, `SafeMarkdown` for chat rendering.
- **Prevent SQL Injection**: All DB queries use parameterized statements (never string interpolation)
- **Prevent Prompt Injection**: Chat endpoint scans messages with 27 regex patterns; score ≥0.8 rejects request
- **Prevent SSRF**: URL validation blocks `javascript:`, `data:`, `vbscript:`, and private IP ranges
- **Rate limiting**: 30 req/min for chat/agent, 120 req/min for general API
- **Audit logging**: Every request gets a `request_id`; security events logged with severity
- **CSP headers**: Content-Security-Policy generated in production via `security.generate_csp_header()`

## ⚡ Performance Guidelines
- Avoid unnecessary re-renders or loops
- Optimize database queries (use R-Tree spatial index)
- Use caching when appropriate (LRU cache on ML inference)
- Lazy-load heavy models (torch/transformers add ~2GB)

## 🧪 Testing & Debugging
- Write testable code
- Add basic error handling
- Log meaningful debug information
- Run `pytest tests/test_api.py -v` before committing changes

## 🧩 Task Execution Strategy
When given a task:
1. Understand the requirement
2. Check existing implementation
3. Plan minimal changes
4. Implement step-by-step
5. Test the result
6. Refactor if needed

## 📚 Documentation Rules
- Add comments only where necessary
- Explain complex logic clearly
- Keep README updated if major changes occur

## 🚫 What to Avoid
- Overengineering
- Unnecessary dependencies
- Hardcoded values
- Ignoring existing patterns
- Bypassing security validation

## 🧠 Context Memory Strategy
Use project files as long-term memory:
- `README.md` → project overview
- `AGENTS.md` → rules (this file)
- `backend/security.py` → centralized security utilities (USE THESE!)
- `backend/` → API and ML modules
- `frontend/` → React UI components

Always refer to these before making decisions.

## 🛠️ Tech Stack
- Frontend: React 18 + Vite + MapLibre GL JS + Tailwind CSS
- Backend: Python (FastAPI + Uvicorn)
- Database: SQLite with R-Tree spatial index
- ML: HuggingFace Transformers + ONNX Runtime
- ETL: Async Python (aiohttp)
- MLOps: Custom drift detection + model registry
- Deployment: Docker on Hugging Face Spaces

## ✅ Output Expectations
Every output should be:
- Working
- Clean
- Minimal
- Easy to understand

## 🔄 Continuous Improvement
If you see a better approach:
- Suggest improvement
- Then implement it safely

## 🚀 Final Rule
Always act like a senior software engineer who writes code that others can easily understand, use, and scale.
