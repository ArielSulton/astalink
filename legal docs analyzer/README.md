# ⚖️ Legal Document Analyzer

A high-performance, full-stack AI platform built to parse, summarize, and analyze complex legal documents with industrial-grade precision. By combining **Agentic RAG** with **Intelligent Model Routing**, this application delivers professional legal insights while maintaining extreme cost efficiency and privacy.

---

## 🌟 Core Innovations

### 1. Intelligent Autonomous Routing (Cost Optimizer)
The app features a "Brain" node built with **LangGraph.js** that pre-analyzes every user query. 
- **Fast Path (Llama-3-8B)**: If the query is a simple fact extraction (e.g., "Who are the parties?"), it routes to the fast 8B model.
- **Reasoning Path (Llama-3-70B)**: If the query requires complex synthesis or risk assessment (e.g., "Analyze the liability risks in Section 4"), it routes to the powerful 70B model.
- **Result**: You get the intelligence of the largest models with the speed and low cost of the smallest.

### 2. Local Privacy-First Embeddings
Unlike standard RAG apps that pay OpenAI for every document chunk vectorized, this app uses **Transformers.js** to run the `all-MiniLM-L6-v2` model **locally on your server**.
- **$0 Vectorization Cost**: Process 100 or 10,000 pages for free.
- **Privacy**: Your document content stays within your execution environment during the embedding phase.

### 3. Personalization Engine
The AI isn't just a generic chatbot. Through `src/lib/personalization.md`, you can define:
- **Tone**: (e.g., "Senior Indonesian Legal Counsel")
- **Structure**: Force the AI to always include a "Risk Assessment" or "Executive Summary".
- **Formatting**: Mandate the use of tables for clause comparisons.

---

## 🛠️ Technical Architecture

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 15 (App Router), Tailwind CSS 4, Lucide React |
| **Backend API** | Next.js API Routes (Serverless-ready TypeScript) |
| **Orchestration** | LangChain.js & LangGraph.js |
| **Database** | Supabase (PostgreSQL) |
| **Vector Search** | `pgvector` extension via Drizzle ORM |
| **LLM Provider** | Groq (Llama 3.1 8B & 70B) |
| **PDF Parsing** | `pdf-parse` with Recursive Character Chunking |

---

## 📋 Installation & Deployment

### Step 1: Database Setup (Supabase)
1. Initialize a new project on [Supabase](https://supabase.com/).
2. Run this SQL in the **SQL Editor** to enable vectors:
   ```sql
   create extension if not exists vector;
   ```

### Step 2: Environment Configuration
Create a `frontend/.env.local` file with the following:
```env
# Get from Supabase Project Settings -> Database -> Connection String (URI)
# IMPORTANT: Use the "Transaction" mode string for best performance.
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"

# Get from https://console.groq.com/keys
GROQ_API_KEY="gsk_..."
```

### Step 3: Launch
```bash
cd frontend
npm install

# Sync the database schema automatically
npm run db:push

# Start the application
npm run dev
```

---

## 📖 Operational Guide

### 📂 Moving the Project
If you need to move the project to a new folder or machine, **only copy these**:
- `src/` (All logic)
- `public/` (Assets)
- `package.json` (Dependency list)
- `.env.local` (Your keys)
- `drizzle.config.ts` & `tsconfig.json` (Configs)

**Do NOT copy** `node_modules/` or `.next/`. These will be recreated automatically when you run `npm install`.

### 📝 Customizing the AI
Edit **`src/lib/personalization.md`** to change how the AI speaks and formats its answers. No code changes required; the AI reads this file fresh on every query.

### 🔄 Database Migrations
If you modify `src/db/schema/documents.ts`:
1. `npm run db:generate` (Creates the SQL migration file)
2. `npm run db:migrate` (Applies it to Supabase)

---

## ⚠️ Troubleshooting

- **404 on Upload**: Ensure you are running the latest version of the code where the route is located at `api/documents/upload`.
- **Large PDF Timeout**: If a 50+ page PDF fails, check your terminal. I have implemented **Batch Processing** (5 chunks at a time) to prevent this, but very large files may require a longer timeout setting in your hosting provider (e.g., Vercel).
- **Vector Search Errors**: Ensure you ran `create extension if not exists vector;` in your Supabase SQL Editor.

---
*Developed for professional legal analysis workflows. AI outputs should be verified by a human attorney.*

## 🗺️ Future Roadmap

Planned enhancements to elevate the **Legal Document Analyzer** to an enterprise-grade platform:

1.  **✨ UI Polish (Enterprise Grade)**: Migration of standard components to **Shadcn UI** for a premium, accessible interface.
2.  **🗂️ Multi-Document Context Management**: Sidebar document management allowing users to toggle specific documents or folders for scoped analysis.
3.  **🔐 Secure Private Vaults**: Integration of **Supabase Auth** to provide private, encrypted document storage per user.
4.  **📄 Professional Export**: One-click generation of **PDF/Word** reports based on AI analysis, formatted for legal review.
5.  **🐳 Cloud-Ready Deployment**: Full **Docker** support and optimized CI/CD pipelines for Vercel/Netlify.
