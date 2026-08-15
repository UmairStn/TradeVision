import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, ShieldCheck, KeyRound } from 'lucide-react';
import { supabase } from '../lib/supabase';

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [otp, setOtp] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password || !confirm) {
      setError('Please fill in all fields');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    
    setLoading(true);
    setError('');

    // Sign up with Supabase
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: name,
        }
      }
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
    } else if (data.session) {
      // If email confirmations are turned off in Supabase, it returns a session immediately!
      navigate('/dashboard');
    } else {
      // Email confirmation is required
      setIsVerifying(true);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otp) {
      setError('Please enter the verification code');
      return;
    }

    setLoading(true);
    setError('');

    const { error: verifyError } = await supabase.auth.verifyOtp({
      email,
      token: otp,
      type: 'signup'
    });

    setLoading(false);

    if (verifyError) {
      setError(verifyError.message);
    } else {
      navigate('/dashboard');
    }
  };

  // Simple password strength indicator
  const getStrength = (pass: string) => {
    if (pass.length === 0) return 0;
    if (pass.length < 6) return 1; // weak
    if (pass.length < 10) return 2; // medium
    return 3; // strong
  };
  const strength = getStrength(password);

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-primary p-4 py-12">
      <div className="w-full max-w-md bg-primary border border-border rounded-2xl shadow-xl p-8 relative overflow-hidden">
        
        <div className="relative z-10 text-center mb-8">
          <div className="mx-auto w-12 h-12 bg-accent-green/10 text-accent-green rounded-xl flex items-center justify-center mb-4">
            {isVerifying ? <KeyRound className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
          </div>
          <h1 className="text-2xl font-bold text-text-primary">
            {isVerifying ? 'Verify Your Email' : 'Create an Account'}
          </h1>
          <p className="text-text-secondary mt-2">
            {isVerifying 
              ? 'We sent an 8-digit code to your email.' 
              : 'Start predicting CSE trends today'}
          </p>
        </div>

        {isVerifying ? (
          <form onSubmit={handleVerify} className="relative z-10 space-y-4">
            {error && (
              <div className="p-3 bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm rounded-lg text-center">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Verification Code</label>
              <div className="relative">
                <input 
                  type="text" 
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="w-full px-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all tracking-[0.5em] text-center text-xl font-mono"
                  placeholder="--------"
                  maxLength={8}
                />
              </div>
            </div>
            <button 
              type="submit"
              disabled={loading}
              className="w-full py-3 mt-4 rounded-xl bg-accent-green text-white font-semibold hover:bg-accent-green/90 transition-all shadow-lg shadow-accent-green/20 disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify Code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="relative z-10 space-y-4">
            {error && (
              <div className="p-3 bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm rounded-lg text-center">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
                  placeholder="Kasun Perera"
                />
              </div>
            </div>

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
              <label className="block text-sm font-medium text-text-primary mb-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
                <input 
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
                  placeholder="Create a strong password"
                />
              </div>
              {/* Strength meter */}
              {password.length > 0 && (
                <div className="flex space-x-1 mt-2">
                  <div className={`h-1.5 flex-1 rounded-full ${strength >= 1 ? 'bg-accent-red' : 'bg-border'}`}></div>
                  <div className={`h-1.5 flex-1 rounded-full ${strength >= 2 ? 'bg-yellow-500' : 'bg-border'}`}></div>
                  <div className={`h-1.5 flex-1 rounded-full ${strength >= 3 ? 'bg-accent-green' : 'bg-border'}`}></div>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
                <input 
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-secondary border border-border rounded-xl text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent transition-all"
                  placeholder="Repeat your password"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full py-3 mt-2 rounded-xl bg-accent-green text-white font-semibold hover:bg-accent-green/90 transition-all shadow-lg shadow-accent-green/20 disabled:opacity-50"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>
        )}

        {!isVerifying && (
          <p className="mt-6 text-center text-sm text-text-secondary relative z-10">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-text-primary hover:text-accent-green transition-colors">
              Log In &rarr;
            </Link>
          </p>
        )}
      </div>
    </div>
  );
};

