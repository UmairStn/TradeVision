# TradeVision 📈

TradeVision is a modern, responsive web application prototype designed for analyzing and predicting trends in the Colombo Stock Exchange (CSE). Built with React, TypeScript, Vite, and Tailwind CSS, it offers a sleek user interface with AI prediction placeholders, real-time charting, and portfolio tracking.

## ✨ Features

- **Dynamic Theme System**: Fully integrated Light/Dark mode with seamless transitions.
- **Stock Analyzer**: Search for CSE stocks, view real-time data, and analyze trends using interactive area charts (via Recharts).
- **AI Predictions Panel**: Provides estimated next-day price movements and confidence scores based on mock algorithms.
- **Portfolio Dashboard**: Track active holdings, calculate daily P&L, and monitor a custom watchlist.
- **Market Overview**: View top gainers, losers, and most active stocks at a glance.
- **Authentication UI**: Clean, glassmorphism-styled login and registration flows with password strength validation.

## 🛠️ Tech Stack

- **Frontend**: React 19, TypeScript
- **Build Tool**: Vite (with Rolldown/SWC)
- **Styling**: Tailwind CSS v4, custom CSS variables
- **Routing**: React Router v7
- **Icons**: Lucide React
- **Charts**: Recharts
- **Containerization**: Docker & Nginx

## 🚀 Getting Started

You can run TradeVision using either Docker (recommended for consistency) or natively using NPM.

### Option 1: Running with Docker (Recommended)

The project includes a multi-stage Docker setup for both development (with hot-reloading) and production.

1. Ensure Docker Desktop is running on your machine.
2. Start the development environment:
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.

*Note: To stop the container, press `Ctrl + C` or run `docker compose -f docker/docker-compose.yml down`.*

### Option 2: Running Locally with NPM

1. Install the dependencies:
   ```bash
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.

## 📁 Project Structure

```
src/
├── components/       # Reusable UI elements (Navbar, Footer, LiveChart, etc.)
├── context/          # Global state management (ThemeContext, StockContext)
├── pages/            # Main application views (Home, Dashboard, Analyzer, etc.)
├── services/         # API layer and mock data generation (api.ts)
├── types/            # TypeScript interfaces and type definitions
├── index.css         # Global styles and Tailwind configuration
└── App.tsx           # Application root and route definitions
```

## ⚠️ Disclaimer

This application is a **prototype** built for educational purposes. All stock data, prices, and AI predictions are currently powered by a mock API service (`src/services/api.ts`) and do not represent real-time financial data. **Do not use this for actual financial trading or advice.**

---
*Developed by Kashwinth*
