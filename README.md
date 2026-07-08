# TradeVision 📈

## Overview
TradeVision is a modern, responsive web application designed for analyzing and predicting trends in the Colombo Stock Exchange (CSE). 

## Problem Statement
The Colombo Stock Exchange (CSE) can be volatile and difficult to navigate for individual investors and casual traders. Existing platforms often lack modern, user-friendly interfaces, real-time interactive analysis tools, and accessible predictive insights. Traders struggle to quickly identify trends, manage their portfolios efficiently, and access AI-driven predictions without relying on complex, enterprise-grade software.

## Solution
TradeVision bridges this gap by providing an intuitive, accessible web platform tailored for the CSE. It empowers users with:
- **Simplified Analysis**: Interactive, real-time charting that makes market trends easy to visualize.
- **AI-Powered Insights**: An integrated prediction panel that offers estimated price movements and confidence scores, making advanced analytics accessible to everyone.
- **Centralized Tracking**: A comprehensive portfolio dashboard to monitor holdings, daily P&L, and custom watchlists in one place.

## ✨ Key Features
- **Stock Analyzer**: Search for CSE stocks and analyze trends using interactive area charts.
- **AI Predictions Panel**: Get estimated next-day price movements and confidence scores.
- **Portfolio Dashboard**: Track active holdings, calculate daily P&L, and monitor a custom watchlist.
- **Market Overview**: View top gainers, losers, and most active stocks at a glance.
- **Dynamic Theme System**: Fully integrated Light/Dark mode with seamless transitions.

## 🛠️ Tech Stack
- **Frontend**: React 19, TypeScript
- **Build Tool**: Vite (with Rolldown/SWC)
- **Styling**: Tailwind CSS v4
- **Charts**: Recharts
- **Containerization**: Docker & Nginx

## 🚀 Getting Started

### Running with Docker (Recommended)
1. Ensure Docker Desktop is running.
2. Start the development environment:
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.

### Running Locally with NPM
1. Install dependencies: `npm install`
2. Start the server: `npm run dev`
3. Open [http://localhost:5173](http://localhost:5173) in your browser.

## ⚠️ Disclaimer
This application is a **prototype** built for educational purposes. All stock data, prices, and AI predictions are currently powered by a mock API service and do not represent real-time financial data. **Do not use this for actual financial trading or advice.**

