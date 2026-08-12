import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { StockProvider } from './context/StockContext';
import { ChatProvider } from './context/ChatContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/Auth/ProtectedRoute';

// Components
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ChatWidget } from './components/ChatWidget';

// Pages
import { Home } from './pages/Home';
import { StockAnalyzer } from './pages/StockAnalyzer';
import { TopStocks } from './pages/TopStocks';
import { Dashboard } from './pages/Dashboard';
import { Chat } from './pages/Chat';
import { Login } from './pages/Login';
import { Register } from './pages/Register';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <StockProvider>
          {/* Inside StockProvider: chat surfaces sit alongside market data, and the
              widget lives inside the router so it can read the current route. */}
          <ChatProvider>
            <BrowserRouter>
            <div className="min-h-screen bg-primary text-text-primary flex flex-col font-sans transition-colors duration-300">
              <Navbar />
              <main className="flex-grow">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/analyzer" element={<StockAnalyzer />} />
                  <Route path="/top-stocks" element={<TopStocks />} />
                  <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                  <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                </Routes>
              </main>
              <Footer />
              <ChatWidget />
            </div>
            </BrowserRouter>
          </ChatProvider>
        </StockProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
