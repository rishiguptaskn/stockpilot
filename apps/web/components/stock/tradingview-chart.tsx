'use client';

/**
 * TradingView chart embed — free tier widget via iframe.
 * Dark theme, candlesticks, daily interval by default.
 *
 * We use the iframe embed rather than tv.js to avoid loading external scripts
 * (satisfies CSP-first mindset). All configuration is via URL params.
 */

interface Props {
  symbol: string; // e.g., "NSE:RELIANCE"
  interval?: '1' | '5' | '15' | '60' | '240' | 'D' | 'W' | 'M';
  theme?: 'light' | 'dark';
  height?: number;
}

export function TradingViewChart({
  symbol,
  interval = 'D',
  theme = 'dark',
  height = 520,
}: Props) {
  const params = new URLSearchParams({
    frameElementId: 'tradingview_widget',
    symbol,
    interval,
    hidesidetoolbar: '0',
    symboledit: '0',
    saveimage: '1',
    toolbarbg: theme === 'dark' ? '18181B' : 'FFFFFF',
    theme,
    studies: '["MASimple@tv-basicstudies","MASimple@tv-basicstudies","RSI@tv-basicstudies","Volume@tv-basicstudies"]',
    studies_overrides: JSON.stringify({
      'MASimple.length': 50,
      'MASimple@0.length': 200,
    }),
    hideideas: '1',
    style: '1',
    locale: 'en',
    withdateranges: '1',
    allow_symbol_change: '1',
    calendar: '1',
  });

  const src = `https://s.tradingview.com/widgetembed/?${params.toString()}`;

  return (
    <div className="relative w-full" style={{ height }}>
      <iframe
        src={src}
        title={`TradingView chart: ${symbol}`}
        style={{
          width: '100%',
          height: '100%',
          border: '0',
          borderRadius: 'inherit',
        }}
        loading="lazy"
        allowFullScreen
      />
    </div>
  );
}
