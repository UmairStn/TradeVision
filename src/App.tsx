import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { StockProvider } from './context/StockContext';

// Components
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';

// Pages
import { Home } from './pages/Home';
import { StockAnalyzer } from './pages/StockAnalyzer';
import { TopStocks } from './pages/TopStocks';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { Register } from './pages/Register';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <StockProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-primary text-text-primary flex flex-col font-sans transition-colors duration-300">
            <Navbar />
            <main className="flex-grow">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/analyzer" element={<StockAnalyzer />} />
                <Route path="/top-stocks" element={<TopStocks />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
              </Routes>
            </main>
            <Footer />
          </div>
        </BrowserRouter>
      </StockProvider>
    </ThemeProvider>
  );
};

export default App;
