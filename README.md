# TradeVision 📈

> 🚧 **Work in Progress** — This project is currently under active development. Core features are being implemented, and additional AI capabilities are continuously being integrated.

TradeVision is a modern, responsive web application for analyzing and predicting trends in the **Colombo Stock Exchange (CSE)**. It combines interactive market visualization with AI-powered stock predictions to help investors better understand market movements and make more informed decisions.

*This project is being developed as a 4th-year capstone project.*

---

# Overview

The Colombo Stock Exchange (CSE) can be volatile and difficult to navigate for individual investors and casual traders. Existing platforms often lack modern, user-friendly interfaces, real-time interactive analysis tools, and accessible predictive insights. Traders struggle to quickly identify trends, manage their portfolios efficiently, and access AI-driven predictions without relying on complex, enterprise-grade software.

TradeVision bridges this gap by providing an intuitive, accessible platform tailored for the CSE. It combines technical market analysis with AI-driven insights in a clean, responsive interface designed for both new and experienced investors.

---

# Problem Statement

Traditional stock prediction models often rely solely on historical price data, which has limited predictive power in many financial markets. Market sentiment from financial news can significantly influence price movements before they appear in technical indicators.

TradeVision addresses this challenge by combining multiple sources of information to provide richer, more informed market insights rather than relying on technical analysis alone.

---

# Solution

TradeVision empowers users with:

- 📈 **Simplified Analysis** – Interactive charts that make market trends easy to understand.
- 🤖 **AI-Powered Predictions** – Estimated next-day price movements with confidence scores.
- 💬 **Intelligent Chatbot** – Ask questions about stocks using natural language.
- 📊 **Portfolio Dashboard** – Track holdings, daily P&L, and watchlists in one place.
- 📉 **Market Overview** – View top gainers, losers, and most active stocks.
- 🌙 **Dynamic Theme System** – Seamless Light/Dark mode experience.

---

# ✨ Key Features

### 📊 Stock Analyzer
- Search and analyze CSE-listed stocks.
- Interactive area charts for historical price visualization.
- Technical trend analysis.

### 🤖 AI Prediction Engine
- Estimated next-day stock price prediction.
- Prediction confidence scores.
- Combines technical indicators with financial news sentiment.

### 💬 AI Chatbot
- Natural language interface for stock-related questions.
- Uses Gemini function calling to retrieve real prediction data.
- Provides grounded responses instead of generated guesses.

### 📈 Portfolio Dashboard
- Track investments.
- Monitor daily profit & loss.
- Maintain a personalized watchlist.

### 🌍 Market Overview
- Top gainers.
- Top losers.
- Most active stocks.

### 🎨 Modern UI
- Responsive design.
- Light/Dark mode.
- Built with modern React architecture.

---

# 🏗️ System Architecture

TradeVision combines several components into a unified prediction platform:

- **Technical Prediction** – XGBoost model trained on historical stock prices and trading volume.
- **News Sentiment Analysis** – FinBERT analyzes financial news to determine market sentiment.
- **Fusion Model** – Combines technical and sentiment signals into a final prediction.
- **Ticker Resolution** – Maps company names found in news articles to CSE ticker symbols.
- **Backend API** – Serves predictions, analytics, and chatbot responses.
- **Caching Layer** – Reduces redundant model inference and external API calls for improved performance.

---

# 💬 Chatbot Design

The chatbot uses **Google Gemini's function-calling** capabilities to answer questions using real backend data instead of generating speculative responses.

Examples:

- **"What is the current price of JKH?"**
  - Retrieves the latest stock price from the backend.

- **"Will JKH increase tomorrow?"**
  - Calls the prediction service, combining:
    - XGBoost technical prediction
    - FinBERT sentiment analysis

Gemini interprets user intent, invokes the appropriate backend function, and converts structured results into natural language responses.

---

# 🛠️ Tech Stack

| Layer | Technology |
|--------|------------|
| **Frontend** | React 19, TypeScript |
| **Build Tool** | Vite (Rolldown/SWC) |
| **Styling** | Tailwind CSS v4 |
| **Charts** | Recharts |
| **Technical Prediction** | XGBoost (Python) |
| **Sentiment Analysis** | FinBERT (Python) |
| **Chatbot** | Google Gemini (Function Calling) |
| **Backend** | Python |
| **Containerization** | Docker & Nginx |

---

# 📌 Project Status

| Component | Status |
|-----------|--------|
| Frontend Dashboard | 🚧 In Progress |
| Stock Analyzer | 🚧 In Progress |
| Portfolio Dashboard | 🚧 In Progress |
| AI Prediction Engine | 🚧 In Progress |
| FinBERT Sentiment Analysis | 🚧 In Progress |
| Fusion Prediction Model | 🚧 In Progress |
| Gemini Chatbot | 🚧 In Progress |
| Backend API | 🚧 In Progress |

---

# 🗺️ Roadmap

- [x] Complete XGBoost prediction pipeline
- [x] Integrate FinBERT sentiment analysis
- [x] Finalize fusion prediction model
- [x] Implement ticker resolution
- [x] Complete backend API
- [x] Finish portfolio dashboard
- [ ] Complete chatbot integration
- [ ] End-to-end testing using live CSE data
- [ ] Deploy production version

---

# ⚠️ Disclaimer

This application is currently a **prototype** developed for educational and research purposes.

The current frontend uses **mock stock data and simulated AI predictions** while backend AI services are under development. Predictions and market information **should not be used for actual financial trading or investment decisions**.

---

---

*TradeVision is continuously evolving as development progresses. Additional features, documentation, and deployment instructions will be added in future updates.*
