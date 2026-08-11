import React from 'react';
import { LineChart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-border bg-primary mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center gap-2 mb-4 md:mb-0 text-text-primary">
            <LineChart className="w-5 h-5 text-accent-green" />
            <span className="font-semibold tracking-tight">TradeVision</span>
          </div>
          <div className="text-sm text-text-secondary text-center md:text-right max-w-md">
            <p className="mb-2">This platform is for educational purposes only and serves as a prototype. Not financial advice.</p>
            <p>&copy; {new Date().getFullYear()} TradeVision Prototype. All rights reserved.</p>
          </div>
        </div>
      </div>
    </footer>
  );
};
