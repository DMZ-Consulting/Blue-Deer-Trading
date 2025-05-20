import { useEffect, useState } from 'react'
import { api } from '@/api/api'
import React from 'react'
import { PortfolioEndpoint, PortfolioTrade } from '../utils/types'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowUpRight, ArrowDownRight, Star, TrendingUp, TrendingDown, Percent, Hash } from 'lucide-react'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuCheckboxItem } from '@/components/ui/dropdown-menu'
import { ChevronDown } from 'lucide-react'

interface PortfolioStats {
  totalTrades: number
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  totalProfitLoss: number
  averageRiskRewardRatio: number
}

interface PortfolioStatsProps {
  configName: string
  status: string
  weekFilter?: string
  optionType?: string
}

export default function PortfolioStats({ configName, status, weekFilter, optionType }: PortfolioStatsProps) {
  const [stats, setStats] = useState<PortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const data = await api.portfolio.getStats({
          configName,
          status,
          weekFilter,
          optionType
        })
        setStats(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch portfolio stats')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [configName, status, weekFilter, optionType])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  if (!stats) return <div>No stats available</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Total Trades</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">{stats.totalTrades}</p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Win Rate</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {(stats.winRate * 100).toFixed(1)}%
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Average Win</h3>
        <p className="mt-2 text-3xl font-semibold text-green-600">
          ${stats.averageWin.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Average Loss</h3>
        <p className="mt-2 text-3xl font-semibold text-red-600">
          ${stats.averageLoss.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Profit Factor</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {stats.profitFactor.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Total P/L</h3>
        <p className={`mt-2 text-3xl font-semibold ${
          stats.totalProfitLoss >= 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          ${stats.totalProfitLoss.toFixed(2)}
        </p>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">Avg R:R Ratio</h3>
        <p className="mt-2 text-3xl font-semibold text-gray-700">
          {stats.averageRiskRewardRatio.toFixed(2)}
        </p>
      </div>
    </div>
  )
}

// Helper to extract symbol and type guards
function isRegularPortfolioTrade(t: PortfolioTrade): t is import('../utils/types').RegularPortfolioTrade {
  if (t.trade && typeof t.trade === 'object' && t.trade !== null) {
    const tradeObj = t.trade as Record<string, unknown>;
    return Object.prototype.hasOwnProperty.call(tradeObj, 'symbol') && typeof tradeObj.symbol === 'string';
  }
  return false;
}
function isPortfolioStrategyTrade(t: PortfolioTrade): t is import('../utils/types').PortfolioStrategyTrade {
  if (t.trade && typeof t.trade === 'object' && t.trade !== null) {
    const tradeObj = t.trade as Record<string, unknown>;
    return Object.prototype.hasOwnProperty.call(tradeObj, 'underlying_symbol') && typeof tradeObj.underlying_symbol === 'string';
  }
  return false;
}

// Helper to calculate P/L per contract (same as in PortfolioTable)
function getPnLPerContract(item: PortfolioTrade): number {
  const tradeType = isPortfolioStrategyTrade(item) ? 'Strategy' : (isRegularPortfolioTrade(item) ? 'Regular' : 'Unknown');
  const singleContractPrice = item.avg_entry_price * item.pct_change / 100;
  if (tradeType === 'Strategy') {
    return singleContractPrice * 100;
  }
  // If oneliner starts with a number, multiply by 100
  const startsWithNumber = /^\d/.test(item.oneliner);
  return startsWithNumber ? singleContractPrice * 100 : singleContractPrice;
}

function getStats(trades: PortfolioTrade[]) {
  if (!trades.length) return null;

  // Helper to extract symbol
  function getSymbol(t: PortfolioTrade): string {
    if (isRegularPortfolioTrade(t)) return t.trade.symbol;
    if (isPortfolioStrategyTrade(t)) return t.trade.underlying_symbol;
    return t.oneliner.split(' ')[0] || 'Unknown';
  }

  // Biggest Win
  const biggestWin = trades.reduce((max, t) => (t.realized_pl > (max?.realized_pl ?? -Infinity) ? t : max), null as PortfolioTrade | null);
  // Worst Loss
  const worstLoss = trades.reduce((min, t) => (t.realized_pl < (min?.realized_pl ?? Infinity) ? t : min), null as PortfolioTrade | null);
  // Best Stock (by total P/L)
  const plByStock: Record<string, number> = {};
  trades.forEach(t => {
    const symbol = getSymbol(t);
    plByStock[symbol] = (plByStock[symbol] || 0) + t.realized_pl;
  });
  const bestStock = Object.entries(plByStock).reduce((best, curr) => curr[1] > best[1] ? curr : best, ["", -Infinity]);
  // Most Traded Stock
  const countByStock: Record<string, number> = {};
  trades.forEach(t => {
    const symbol = getSymbol(t);
    countByStock[symbol] = (countByStock[symbol] || 0) + 1;
  });
  const mostTradedStock = Object.entries(countByStock).reduce((most, curr) => curr[1] > most[1] ? curr : most, ["", -Infinity]);
  // Win Rate
  const wins = trades.filter(t => t.realized_pl > 0).length;
  const winRate = trades.length ? (wins / trades.length) * 100 : 0;
  // Average Trade Size (use realized_size)
  const avgSize = trades.length ? trades.reduce((sum, t) => sum + (t.realized_size || 0), 0) / trades.length : 0;
  // Total Trades
  const totalTrades = trades.length;

  return {
    biggestWin,
    worstLoss,
    bestStock,
    mostTradedStock,
    winRate,
    avgSize,
    totalTrades,
  };
}

export function PortfolioStatsCards({ portfolio }: { portfolio: PortfolioEndpoint }) {
  // Stat card config
  const statOptions = [
    { key: 'biggestWin', label: 'Biggest Win' },
    { key: 'worstLoss', label: 'Worst Loss' },
    { key: 'bestStock', label: 'Best Stock' },
    { key: 'mostTradedStock', label: 'Most Traded Stock' },
    { key: 'winRate', label: 'Win Rate' },
    { key: 'avgSize', label: 'Avg Trade Size' },
    { key: 'totalTrades', label: 'Total Trades' },
  ];
  const [visibleStats, setVisibleStats] = React.useState<string[]>([]); // default to all hidden

  const allSelected = visibleStats.length === statOptions.length;
  const noneSelected = visibleStats.length === 0;

  const handleToggle = (key: string) => {
    setVisibleStats(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const handleShowAllToggle = () => {
    if (allSelected) {
      setVisibleStats([]); // Hide all if all are selected
    } else {
      setVisibleStats(statOptions.map(opt => opt.key)); // Show all if none or some are selected
    }
  };

  const allTrades = [...(portfolio.regular_trades || []), ...(portfolio.strategy_trades || [])];
  const stats = getStats(allTrades);
  if (!stats) return null;

  return (
    <div>
      {/* Dropdown to select visible stats */}
      <div className="flex justify-end mb-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center px-3 py-1 bg-gray-800 text-white rounded shadow hover:bg-gray-700">
              Select stats <ChevronDown className="ml-2 w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuCheckboxItem
              checked={allSelected}
              onCheckedChange={handleShowAllToggle}
              className="font-semibold border-b border-gray-200 mb-1"
            >
              Show all
            </DropdownMenuCheckboxItem>
            {statOptions.map(opt => (
              <DropdownMenuCheckboxItem
                key={opt.key}
                checked={visibleStats.includes(opt.key)}
                onCheckedChange={() => handleToggle(opt.key)}
              >
                {opt.label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-6">
        {/* Biggest Win */}
        {visibleStats.includes('biggestWin') && (
          <Card className="bg-gradient-to-br from-green-400 via-emerald-500 to-cyan-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <ArrowUpRight className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Biggest Win</div>
                <div className="text-3xl font-bold drop-shadow">${stats.biggestWin ? getPnLPerContract(stats.biggestWin).toFixed(2) : '--'}</div>
                <div className="text-sm opacity-80">{stats.biggestWin?.oneliner ?? '--'}</div>
                {stats.biggestWin && (
                  <div className="text-xs mt-1 opacity-80">% Change: <span className="font-semibold">{stats.biggestWin.pct_change.toFixed(2)}%</span></div>
                )}
                <div className="text-xs mt-1 opacity-70">P/L per contract for your largest profit</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Worst Loss */}
        {visibleStats.includes('worstLoss') && (
          <Card className="bg-gradient-to-br from-red-400 via-pink-500 to-fuchsia-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <ArrowDownRight className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Worst Loss</div>
                <div className="text-3xl font-bold drop-shadow">${stats.worstLoss ? getPnLPerContract(stats.worstLoss).toFixed(2) : '--'}</div>
                <div className="text-sm opacity-80">{stats.worstLoss?.oneliner ?? '--'}</div>
                {stats.worstLoss && (
                  <div className="text-xs mt-1 opacity-80">% Change: <span className="font-semibold">{stats.worstLoss.pct_change.toFixed(2)}%</span></div>
                )}
                <div className="text-xs mt-1 opacity-70">P/L per contract for your largest loss</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Best Stock */}
        {visibleStats.includes('bestStock') && (
          <Card className="bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <Star className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Best Stock</div>
                <div className="text-2xl font-bold drop-shadow">{stats.bestStock[0]}</div>
                <div className="text-lg text-blue-100">${stats.bestStock[1].toFixed(2)}</div>
                <div className="text-xs mt-1 opacity-70">Stock with highest total P/L</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Most Traded Stock */}
        {visibleStats.includes('mostTradedStock') && (
          <Card className="bg-gradient-to-br from-yellow-400 via-orange-500 to-rose-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <TrendingUp className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Most Traded Stock</div>
                <div className="text-2xl font-bold drop-shadow">{stats.mostTradedStock[0]}</div>
                <div className="text-lg text-yellow-100">{stats.mostTradedStock[1]} trades</div>
                <div className="text-xs mt-1 opacity-70">Stock with the most trades</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Win Rate */}
        {visibleStats.includes('winRate') && (
          <Card className="bg-gradient-to-br from-indigo-400 via-blue-500 to-cyan-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <Percent className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Win Rate</div>
                <div className="text-3xl font-bold drop-shadow">{stats.winRate.toFixed(1)}%</div>
                <div className="text-xs mt-1 opacity-70">% of trades with positive P/L</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Avg Trade Size */}
        {visibleStats.includes('avgSize') && (
          <Card className="bg-gradient-to-br from-purple-400 via-fuchsia-500 to-pink-500 shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <TrendingDown className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Avg Trade Size</div>
                <div className="text-3xl font-bold drop-shadow">{stats.avgSize.toFixed(2)}</div>
                <div className="text-xs mt-1 opacity-70">Average size of all trades</div>
              </div>
            </CardContent>
          </Card>
        )}
        {/* Total Trades */}
        {visibleStats.includes('totalTrades') && (
          <Card className="bg-gradient-to-br from-gray-700 via-gray-900 to-black shadow-xl border-0 text-white relative overflow-hidden">
            <CardContent className="flex items-center gap-4 py-6">
              <Hash className="w-10 h-10 opacity-80" />
              <div>
                <div className="text-lg font-semibold">Total Trades</div>
                <div className="text-3xl font-bold drop-shadow">{stats.totalTrades}</div>
                <div className="text-xs mt-1 opacity-70">Number of trades in this period</div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
} 