'use client';

import { useState, useEffect } from 'react';
import { getTrades } from '@/utils/api';

interface Trade {
  trade_id: string;
  symbol: string;
  trade_type: string;
  entry_price: number;
  current_size: string;
}

export default function Home() {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const tradesData = await getTrades();
        setTrades(tradesData);
      } catch (error) {
        console.error('Error fetching trades:', error);
      }
    };

    fetchTrades();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <h1 className="text-4xl font-bold mb-8">Trades</h1>
      <ul className="space-y-4">
        {trades.map((trade) => (
          <li key={trade.trade_id} className="bg-gray-100 p-4 rounded-lg">
            <h2 className="text-xl font-semibold">{trade.symbol}</h2>
            <p>Type: {trade.trade_type}</p>
            <p>Entry Price: ${trade.entry_price.toFixed(2)}</p>
            <p>Current Size: {trade.current_size}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
