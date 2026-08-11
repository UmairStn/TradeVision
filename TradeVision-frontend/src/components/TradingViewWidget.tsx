import React, { useEffect, useRef, memo } from 'react';
import { useTheme } from '../context/ThemeContext';

export const TradingViewWidget: React.FC = memo(() => {
  const widgetContainerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (!widgetContainerRef.current) return;

    // Clear previous widget elements inside the container
    widgetContainerRef.current.innerHTML = '';

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    
    const bgColor = theme === 'dark' ? '#0f172a' : '#ffffff';
    const gridColor = theme === 'dark' ? 'rgba(242, 242, 242, 0.06)' : 'rgba(0, 0, 0, 0.06)';

    script.innerHTML = JSON.stringify({
      "allow_symbol_change": true,
      "calendar": false,
      "details": false,
      "hide_side_toolbar": true,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "hide_volume": false,
      "hotlist": false,
      "interval": "D",
      "locale": "en",
      "save_image": true,
      "style": "1",
      "symbol": "CSELK:COMB.N0000",
      "theme": theme,
      "timezone": "Asia/Colombo",
      "backgroundColor": bgColor,
      "gridColor": gridColor,
      "watchlist": [],
      "withdateranges": false,
      "compareSymbols": [],
      "studies": [],
      "autosize": true
    });
    
    widgetContainerRef.current.appendChild(script);

    return () => {
      if (widgetContainerRef.current) {
        widgetContainerRef.current.innerHTML = '';
      }
    };
  }, [theme]);

  return (
    <div className="tradingview-widget-container flex flex-col h-full w-full">
      <div 
        ref={widgetContainerRef} 
        className="tradingview-widget-container__widget flex-grow w-full"
        style={{ height: 'calc(100% - 32px)' }} 
      />
      <div className="tradingview-widget-copyright text-center py-2 text-xs text-text-secondary border-t border-border/50 bg-secondary/30">
        <a 
          href="https://www.tradingview.com/symbols/CSELK-COMB.N0000/" 
          rel="noopener nofollow" 
          target="_blank" 
          className="text-accent-green hover:underline font-medium"
        >
          COMB.N0000 Stock Chart
        </a>
        <span className="text-text-secondary"> by TradingView</span>
      </div>
    </div>
  );
});

TradingViewWidget.displayName = 'TradingViewWidget';
