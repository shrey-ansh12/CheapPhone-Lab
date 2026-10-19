# CheapPhone Lab — Test Beyond the Flagship
> **HackFront India 2026** | Problem Statement: T1.2 — AI & Developer Tools
> **Target Track:** Neo4j Graph Database Partner Track

---

## 📌 Executive Summary
**CheapPhone Lab** is a developer platform designed to help engineering teams discover, understand, and prioritize application failures under realistic Indian mobile conditions — including **slow 2G/3G speeds**, **intermittent network deadzones**, **low internal storage (< 500MB)**, **memory pressure (1GB / 2GB RAM Go edition phones)**, **battery saver CPU throttling**, and **process eviction**.

Developers frequently build and test on flagship hardware (8GB+ RAM, 5G / High-speed Wi-Fi), inadvertently shipping catastrophic Out-of-Memory crashes (OOM), looper ANRs, and duplicate payment transactions to the 400M+ Indian users on budget devices. **CheapPhone Lab brings testing beyond the flagship.**

---

## 🛠️ Tech Stack (Strictly Implemented)
- **Frontend:** Vanilla HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js, Vis-network, Lucide Icons.
- **Backend:** Python 3.11+, Flask with RESTful JSON endpoints.
- **Database:** **Neo4j AuraDB** (primary graph engine) with seamless local JSON store fallback for disconnected demo runs.
- **Android Diagnostics:** Android Debug Bridge (ADB), Logcat collector, subprocess argument-list runner.
- **Testing & Exports:** pytest, JSON & Markdown reproduction report generator.

---

## 🏗️ Architecture Overview

```
                               ┌───────────────────────────────────────────────┐
                               │           CheapPhone Lab Web UI               │
                               │  (Dark Navy / Charcoal Developer Dashboard)   │
                               └──────────────────────┬────────────────────────┘
                                                      │ HTTP / JSON
                                                      ▼
                               ┌───────────────────────────────────────────────┐
                               │               Flask Core Engine               │
                               │  (Routes, Validation, Auth & Session Control) │
                               └───────┬───────────────────────────────┬───────┘
                                       │                               │
                      ┌────────────────┴──────────────┐  ┌─────────────┴─────────────┐
                      ▼                               ▼  ▼                           ▼
        ┌─────────────────────────┐     ┌───────────────────────┐      ┌─────────────────────────┐
        │ Mode A: Demo Simulation │     │ Mode B: Real ADB Test │      │     Impact Analyzer     │
        │ Deterministic Mobile    │     │ Controlled Logcat &   │      │ User Reach & Priority   │
        │ Stress Rules (No Phone) │     │ Screenshot Capture    │      │ Scoring Algorithm       │
        └─────────────┬───────────┘     └───────────┬───────────┘      └─────────────┬───────────┘
                      │                             │                                │
                      └──────────────────────┬──────┴────────────────────────────────┘
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │        Neo4j AuraDB Graph Engine              │
                      │  - Multi-hop Pattern Matching (Cypher)        │
                      │  - Application ──> Feature ──> Failure        │
                      │  - TestRun ──> Condition ──> UserSegment      │
                      │  - Disconnected fallback to local data store  │
                      └───────────────────────────────────────────────┘
```

---

## 🚀 5-Minute Hackathon Demonstration Script

### Step 1: Open Dashboard (`0:00 - 0:45`)
1. Launch the server (`python app.py`) and navigate to `http://localhost:5000`.
2. **Key Talking Point:** Show the high-contrast developer theme and live stats: *Total Test Runs*, *Critical/High Failures*, and *Failure Distribution by Category* powered by Chart.js.
3. Note the bottom-left sidebar status indicator: Shows live Neo4j AuraDB status or graceful offline demo storage.

### Step 2: Configure a Stress Run in Test Lab (`0:45 - 1:45`)
1. Click **Test Lab** on the sidebar.
2. Select **Mode A: Demo Simulation** (highlight that the app is 100% functional on any machine without physical phones).
3. Set:
   - Application: `KisanBazaar Grocery App`
   - Target Profile: `BharatPhone Lite (2GB / Android 10 Go)`
   - Network Condition: `Slow connection (128kbps / 2G EDGE)`
   - Available Storage: `Low (Under 500MB)`
   - Memory Pressure: `High`
   - Battery Saver: `Enabled`
4. Click **Execute Simulation Run**.

### Step 3: Inspect Discovered Failures & Reproduction Recipes (`1:45 - 2:45`)
1. The app redirects to the **Test Run Details** page (`RUN_SIM_...`).
2. Show the discovered failures:
   - *Out of Memory (OOM) Fatal Crash on Image Bitmap Decode*
   - *Checkout Payment Gateway 30s Socket Timeout*
   - *SQLite Disk Full Error on Offline Sync Cache*
3. Drill into a **Reproduction Recipe**:
   - Highlight exact preconditions, step-by-step instructions, and suggested debugging directions (e.g. *Downsample bitmaps using RGB_565 and Coil/Glide*).
   - Show raw diagnostic evidence and Logcat stack traces.

### Step 4: Transparent User Impact Analysis (`2:45 - 3:30`)
1. Navigate to **Impact Analysis**.
2. **Key Talking Point:** Explain the transparent formula:
   $$\text{Affected Users} = \text{Target Population} \times \text{Condition Prevalence} \times \text{Failure Probability}$$
3. Adjust target user base from 5,000,000 to 10,000,000 or tweak $\le$ 2GB RAM prevalence to show dynamic re-ranking.
4. Show priority action badges: P0 Hotfix Blocker vs P2 Scheduled Polish.

### Step 5: Neo4j Graph Explorer (`3:30 - 4:30`)
1. Navigate to **Graph Explorer**.
2. **Key Talking Point (Neo4j Partner Track):**
   - Click and drag nodes on the interactive **vis-network** canvas.
   - Show how Neo4j connects `Application -> AppFeature <- Failure <- TestRun -> Condition -> UserSegment`.
   - Point out pattern matching: *Explain how two seemingly disparate crashes (Catalog OOM and Startup ANR) share the exact same underlying Condition node (2GB RAM / Battery Saver)*.
   - Explain how relational databases fail at cross-run topological queries that Neo4j solves in milliseconds with Cypher `MATCH` queries.

### Step 6: Export Reports (`4:30 - 5:00`)
1. Go to **Reports** and click **Markdown** / **JSON**.
2. Show the downloaded bug report ready to paste into GitHub Issues or Jira.
3. Conclude with: *"CheapPhone Lab empowers every developer to build inclusive software that never fails the next billion users."*

---

## ⚙️ Installation & Quickstart

### Prerequisites
- Python 3.10+
- (Optional) Android Studio / ADB if testing physical devices

### 1. Clone & Setup
```bash
git clone <repo-url>
cd hackfront

# Install dependencies
python -m pip install -r requirements.txt
```

### 2. Configure Environment (.env)
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
To connect a live **Neo4j AuraDB** instance:
```env
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-aura-password>
```
*(If left empty, CheapPhone Lab automatically and gracefully activates the high-fidelity offline store without crashing or throwing errors).*

### 3. Run Automated Tests
```bash
python -m pytest tests/test_core.py -v
```

### 4. Launch Application
```bash
python app.py
```
Open **`http://localhost:5000`** in your browser.

---

## 📦 Features & Limitations

### Working Features
- ✅ **9 Dedicated Pages:** Dashboard, Test Lab, Test Runs, Failure Explorer, Impact Analysis, Graph Explorer, Device Profiles, Reports, Settings.
- ✅ **Deterministic Simulation Engine:** Repeatable stress conditions modeling low memory, 2G latency, full storage, and process death.
- ✅ **Real ADB Integration:** Auto-detects connected emulators, queries device properties (`getprop`), and parses Logcat streams for fatal errors.
- ✅ **Neo4j AuraDB Graph:** Real node-relationship schema (`MERGE` queries to prevent duplicates), subgraph neighborhood queries, and interactive visual graph explorer.
- ✅ **Transparent Impact Prioritization:** Configurable user population and condition prevalence calculations with normalized P0-P3 action scores.
- ✅ **Report Exporter:** Formats runs into Markdown and JSON downloads.

### Known Limitations & Planned Extensions
- **Network Traffic Shaping on Real Emulators:** Network preset simulation on physical devices is marked as simulated unless hardware-level root throttling or proxy shaping (e.g. mitmproxy/Charles) is connected.
- **APK Execution Sandboxing:** APK uploads are restricted to `.apk` files and staged for emulator push only; direct server-side execution is intentionally blocked for security.

---

## 🏆 HackFront India 2026 Submission
*Built with pride for Indian developers building for the next billion users.*
