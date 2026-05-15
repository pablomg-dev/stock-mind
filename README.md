# StockMind

<div align="center">

![StockMind](https://img.shields.io/badge/StockMind-AI%20Trading%20Agent-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)

**Autonomous trading agent for xStocks (Kraken CLI + Gemini 2.5 Flash) with real-time React dashboard**

</div>

---

## 🚀 Features

- **AI-Powered Decisions**: Uses Google Gemini 2.5 Flash for intelligent trading decisions
- **Technical Analysis**: RSI, MACD, SMA indicators for market signals
- **Real-Time Dashboard**: React frontend with live WebSocket updates
- **Paper & Live Trading**: Switch between simulation and real trading modes
- **News Sentiment**: Integrates NewsAPI for market sentiment analysis
- **Kraken Integration**: Executes trades via Kraken CLI
- **SQLite Database**: Persistent decision history and tracking

---

## 📋 Requirements

- **Python 3.11+**
- [Kraken CLI](https://github.com/krakenfx/kraken-cli) installed and in `PATH`
- **Node.js 18+** (for the frontend)
- Google AI Studio [API Key](https://aistudio.google.com/app/apikey) (Gemini)
- NewsAPI [API Key](https://newsapi.org/) (optional, for sentiment analysis)

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/pablomg-dev/stock-mind.git
cd stock-mind
```

### 2. Environment Configuration

Copy the example environment file and fill in your API keys:

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**Linux/macOS:**

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_key
KRAKEN_API_KEY=your_kraken_key
KRAKEN_API_SECRET=your_kraken_secret
NEWS_API_KEY=your_news_api_key
TICKER=PF_NVDAXUSD
INTERVAL_MINUTES=15
MODE=paper
```

### 3. Python Dependencies (Virtual Environment Recommended)

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** If activation fails on Windows due to execution policy, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Frontend Dependencies

**Windows PowerShell:**

```powershell
cd frontend
npm install
cd ..
```

**Linux/macOS:**

```bash
cd frontend
npm install
cd ..
```

---

## 🎮 Running the Application

You need **3 separate terminals** to run all components:

### Terminal 1: Trading Agent

```bash
# Activate virtual environment first
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\Activate.ps1  # Windows

# Run the agent
python -m agent.main
```

### Terminal 2: FastAPI Backend

```bash
# Activate virtual environment first
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\Activate.ps1  # Windows

# Start the API server
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3: React Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

---

## 📊 Architecture

```
StockMind/
├── agent/              # Trading agent logic
│   ├── brain.py       # Gemini AI decision engine
│   ├── signals.py     # Technical indicators (RSI, MACD, SMA)
│   ├── executor.py    # Kraken CLI trade execution
│   ├── db.py          # SQLite database operations
│   └── main.py        # Main trading loop
├── api/               # FastAPI backend
│   └── server.py      # REST API + WebSocket server
├── frontend/          # React dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── ReasoningFeed.jsx  # Live decision feed
│   │   │   ├── Portfolio.jsx       # Portfolio display
│   │   │   └── PnLChart.jsx       # P&L chart
│   │   ├── App.jsx
│   │   └── api.js
│   └── public/
│       └── favicon.svg
├── .env.example       # Environment template
├── requirements.txt   # Python dependencies
└── package.json       # Node.js dependencies
```

---

## 🔧 Configuration

### Trading Mode

Set `MODE` in `.env`:

- `paper` - Simulation mode (no real trades)
- `live` - Real trading with Kraken

The dashboard displays a **Paper** or **Live** badge based on this setting.

### API Endpoints

- `GET /decisions` - Get recent trading decisions
- `GET /config` - Get current trading mode
- `WS /ws` - WebSocket for real-time updates

### Environment Variables

| Variable            | Description               | Default        |
| ------------------- | ------------------------- | -------------- |
| `GEMINI_API_KEY`    | Google Gemini API key     | Required       |
| `KRAKEN_API_KEY`    | Kraken API key            | Required       |
| `KRAKEN_API_SECRET` | Kraken API secret         | Required       |
| `NEWS_API_KEY`      | NewsAPI key for sentiment | Optional       |
| `TICKER`            | Trading pair ticker       | `PF_NVDAXUSD`  |
| `INTERVAL_MINUTES`  | Trading loop interval     | `15`           |
| `MODE`              | Trading mode (paper/live) | `paper`        |
| `STOCKMIND_DB_PATH` | SQLite database path      | `stockmind.db` |

---

## 🎨 Tech Stack

### Backend

- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **SQLite** - Database
- **Google Gemini 2.5 Flash** - AI decision engine
- **Kraken CLI** - Trade execution
- **pandas & pandas-ta** - Technical analysis

### Frontend

- **React 18** - UI library
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Recharts** - Data visualization
- **WebSocket API** - Real-time updates

---

## 📝 License

This project is open source and available under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📧 Contact

For questions or support, please open an issue on GitHub.
