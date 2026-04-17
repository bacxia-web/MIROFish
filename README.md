<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

**Fork with Neo4j + Qdrant backend & LLM-based Entity Disambiguation**

[![Live Demo](https://img.shields.io/badge/Demo-Entity%20Disambiguation-6366f1?style=flat-square)](https://bacxia-web.github.io/MIROFish/showcase)
[![Upstream](https://img.shields.io/badge/Upstream-666ghj%2FMiroFish-DAA520?style=flat-square&logo=github)](https://github.com/666ghj/MiroFish)
[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square&color=DAA520&label=upstream%20stars)](https://github.com/666ghj/MiroFish/stargazers)

[简介](#-overview) · [本 Fork 的改动](#-whats-different-in-this-fork) · [实体消歧](#-entity-disambiguation) · [快速上手](#-quick-start) · [致谢](#-acknowledgments)

</div>

---

## ⚡ Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution.

> Upload seed materials → MiroFish returns a detailed prediction report and a deeply interactive high-fidelity digital world.

This repository is a fork of [666ghj/MiroFish](https://github.com/666ghj/MiroFish). The two main contributions are described below.

---

## 🔧 What's Different in This Fork

### 1. Neo4j + Qdrant replaces Zep Cloud

The upstream project relies on [Zep Cloud](https://app.getzep.com/) for graph memory, which introduces a hard external dependency and rate-limit risk in production. This fork replaces it with a fully self-hosted stack:

| Layer | Upstream | This Fork |
|-------|----------|-----------|
| Graph store | Zep Cloud API | **Neo4j** (local / AuraDB) |
| Vector index | Zep built-in | **Qdrant** (local / Qdrant Cloud) |
| Entity memory | `zep-cloud` SDK | `neo4j` driver + `qdrant-client` |

**Why it matters:**
- No third-party quota or billing surprises
- Graph and vector data stay in your own infrastructure
- Swap between local dev and cloud with a single env var change

### 2. LLM-based Entity Disambiguation

Knowledge graphs built from long documents accumulate duplicate nodes — the same real-world entity referenced under slightly different names (e.g. "范禹 (Fan Yu)" vs. "范禹·学生会主席"). This fork adds a dedicated disambiguation pipeline that uses an LLM to identify and merge these duplicates, significantly improving graph quality for downstream simulation and retrieval.

👉 **[View the interactive disambiguation showcase →](https://bacxia-web.github.io/MIROFish/showcase)**

---

## 🔍 Entity Disambiguation

### What it does

After graph construction, the disambiguator:
1. Extracts all entity nodes and groups candidate pairs by name similarity
2. Feeds each pair to an LLM with their relational context
3. Merges confirmed duplicates, re-linking all edges to the canonical node
4. Records every decision for auditability

### Results across 3 real projects

| Project | Model | Nodes (before → after) | Compression | Duplicate groups eliminated |
|---------|-------|------------------------|-------------|----------------------------|
| Wuhan University public opinion | qwen3-coder-flash | 77 → 24 | **−68.8%** | 4 → 0 |
| News event simulation | qwen3-coder-flash | 43 → 22 | **−48.8%** | 2 → 0 |
| Literary character network | qwen3-coder-flash | 18 → 11 | **−38.9%** | 1 → 0 |

**Summary: 3 projects · 17 LLM pair decisions · avg −52% node compression · 100% duplicate elimination**

Graph connectivity improved dramatically after disambiguation:

| | Avg degree (before) | Avg degree (after) | Isolated node ratio (before → after) |
|-|---------------------|--------------------|--------------------------------------|
| Project 1 | 1.82 | **10.08** | 26.0% → **4.2%** |
| Project 2 | 2.42 | **4.09** | 4.7% → **0%** |
| Project 3 | 2.33 | **3.82** | 11.1% → **0%** |

Interactive before/after comparisons with full LLM decision logs are available at the [demo page](https://bacxia-web.github.io/MIROFish/showcase).

---

## 🔄 Workflow

1. **Graph Building** — Seed extraction → chunk embedding → Neo4j graph construction → Qdrant vector index
2. **Entity Disambiguation** — LLM-guided node merging → graph quality metrics
3. **Environment Setup** — Entity relationship extraction → persona generation → agent configuration
4. **Simulation** — Dual-platform parallel simulation (Twitter / Reddit) → dynamic temporal memory updates
5. **Report Generation** — ReportAgent with rich toolset for deep interaction with post-simulation environment
6. **Deep Interaction** — Chat with any agent or the ReportAgent in the simulated world

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Description |
|------|---------|-------------|
| **Node.js** | 18+ | Frontend runtime |
| **Python** | ≥3.11, ≤3.12 | Backend runtime |
| **uv** | Latest | Python package manager (`pip install uv`) |
| **Neo4j** | 5+ | Graph database — [Desktop](https://neo4j.com/download/) or [AuraDB Free](https://neo4j.com/cloud/platform/aura-graph-database/) |
| **Qdrant** | Latest | Vector database — `docker run -p 6333:6333 qdrant/qdrant` |

### 1. Configure environment variables

```bash
cp .env.example .env
```

```env
# LLM (OpenAI-compatible, e.g. Alibaba Qwen via Bailian)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Graph backend — set to "local" to use Neo4j + Qdrant
GRAPH_BACKEND=local

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Qdrant
QDRANT_URL=http://localhost:6333
```

> **Using Zep instead?** Set `GRAPH_BACKEND=zep` and provide `ZEP_API_KEY`. The upstream Zep path is still fully supported.

### 2. Install dependencies

```bash
npm run setup:all
```

### 3. Start services

```bash
npm run dev
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

### Docker (production)

A `Dockerfile.render` is included for single-container deployment (builds the Vue frontend and serves it via Flask). Set `GRAPH_BACKEND`, `NEO4J_*`, and `QDRANT_URL` as environment variables in your platform dashboard.

---

## 📸 Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="Screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="Screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="Screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="Screenshot 4" width="100%"/></td>
</tr>
</table>
</div>

---

## 📄 Acknowledgments

This project builds on [666ghj/MiroFish](https://github.com/666ghj/MiroFish), which received strategic support and incubation from **Shanda Group**.

The simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**. Sincere thanks to the CAMEL-AI team for their open-source contributions.
