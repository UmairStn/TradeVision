import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LineChart, Mail, Lock } from 'lucide-react';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    // Simulate login success & redirect to dashboard
    navigate('/dashboard');
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-primary p-4">
      <div className="w-full max-w-md bg-primary border border-border rounded-2xl shadow-xl p-8 relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-accent-green/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 text-center mb-8">
          <div className="mx-auto w-12 h-12 bg-accent-green/10 text-accent-green rounded-xl flex items-center justify-center mb-4">
            <LineChart className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">Welcome Back</h1>
          <p className="text-text-secondary mt-2">Log in to your CSE Predict account</p>
        </div>

        <form onSubmit={handleSubmit} className="relative z-10 space-y-5">
          {error && (
            <div className="p-3 bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm rounded-lg text-center">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
                placeholder="you@example.com"
              />
            </div>
          </div>
          
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-sm font-medium text-text-primary">Password</label>
              <a href="#" className="text-xs text-accent-green hover:underline">Forgot password?</a>
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
              <input 
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div className="flex items-center">
            <input type="checkbox" id="remember" className="rounded border-border text-accent-green focus:ring-accent-green bg-secondary" />
            <label htmlFor="remember" className="ml-2 text-sm text-text-secondary">Remember me</label>
          </div>

          <button 
            type="submit"
            className="w-full py-3 rounded-xl bg-accent-green text-white font-semibold hover:bg-accent-green/90 transition-all shadow-lg shadow-accent-green/20"
          >
            Log In
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary relative z-10">
          Don't have an account?{' '}
          <Link to="/register" className="font-medium text-text-primary hover:text-accent-green transition-colors">
            Get Started &rarr;
          </Link>
        </p>
      </div>
    </div>
  );
};
