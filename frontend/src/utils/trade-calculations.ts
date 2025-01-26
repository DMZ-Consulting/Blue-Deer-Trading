interface Transaction {
  id: string;
  trade_id: string;
  transaction_type: string;
  amount: number;
  size: string;
  created_at: string;
}

interface TradeState {
  average_price: number | null;
  current_size: string;
  status: 'OPEN' | 'CLOSED';
  closed_at: string | null;
}

export function calculateTradeState(transactions: Transaction[]): TradeState {
  // Sort transactions by created_at to process them in order
  const sortedTransactions = [...transactions].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  let totalCost = 0;    // Total cost basis (positive for buys, negative for sells)
  let totalShares = 0;  // Total shares (positive for buys, negative for sells)

  // Process each transaction
  for (const transaction of sortedTransactions) {
    const shares = parseFloat(transaction.size);
    const cost = transaction.amount * shares;

    switch (transaction.transaction_type) {
      case 'OPEN':
      case 'ADD':
        totalCost += cost;
        totalShares += shares;
        break;
      case 'TRIM':
      case 'CLOSE':
        totalCost -= cost;
        totalShares -= shares;
        break;
    }
  }

  // Calculate the final state
  const state: TradeState = {
    average_price: totalShares !== 0 ? Math.abs(totalCost / totalShares) : null,
    current_size: totalShares > 0 ? totalShares.toString() : '0',
    status: totalShares > 0 ? 'OPEN' : 'CLOSED',
    closed_at: totalShares <= 0 && sortedTransactions.length > 0 ? 
      sortedTransactions[sortedTransactions.length - 1].created_at : 
      null
  };

  return state;
}

// Example usage:
/*
const transactions = [
  {
    id: '1',
    trade_id: 'trade1',
    transaction_type: 'OPEN',
    amount: 100,
    size: '5',
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    trade_id: 'trade1',
    transaction_type: 'ADD',
    amount: 110,
    size: '5',
    created_at: '2024-01-02T00:00:00Z'
  },
  {
    id: '3',
    trade_id: 'trade1',
    transaction_type: 'TRIM',
    amount: 120,
    size: '3',
    created_at: '2024-01-03T00:00:00Z'
  }
];

const state = calculateTradeState(transactions);
console.log(state);
// Output:
// {
//   average_price: 105, // ((100 * 5) + (110 * 5) - (120 * 3)) / (5 + 5 - 3)
//   current_size: '7',  // 5 + 5 - 3
//   status: 'OPEN',     // because current_size > 0
//   closed_at: null     // because trade is still open
// }
*/ 