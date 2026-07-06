/**
 * Formatters — INR currency, percentages, dates, tickers.
 * Use across the entire app for consistency.
 */

const INR_FORMATTER = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const INR_FORMATTER_PRECISE = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatINR(amount: number, precise = false): string {
  return (precise ? INR_FORMATTER_PRECISE : INR_FORMATTER).format(amount);
}

export function formatPercent(value: number, digits = 2): string {
  return `${value.toFixed(digits)}%`;
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

/**
 * Turn "RELIANCE.NS" into "RELIANCE" for display.
 */
export function displayTicker(ticker: string): string {
  return ticker.replace(/\.(NS|BO)$/i, '');
}

export function formatDateShort(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}
