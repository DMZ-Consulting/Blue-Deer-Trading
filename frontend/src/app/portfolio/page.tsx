'use client'

import { useState, useEffect } from 'react'
import { PortfolioTableComponent } from '@/components/PortfolioTable'
import { ReportAreaComponent } from '@/components/ReportArea'
import { Button } from "@/components/ui/button"
import { PanelRightOpen, PanelRightClose } from 'lucide-react'
import { getPortfolio } from '@/api/api'
import { PortfolioEndpoint } from '@/utils/types'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DatePickerWithRange } from '@/components/DatePickerWithRange'
import { DateRange } from 'react-day-picker'
import { startOfWeek, endOfWeek } from 'date-fns'

const TRADE_GROUPS = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" }
] as const;

export default function PortfolioPage() {
  const [configName, setConfigName] = useState(() => {
    // Try to get saved config from localStorage, default to 'day_trader'
    if (typeof window !== 'undefined') {
      return localStorage.getItem('portfolioConfigName') || 'day_trader';
    }
    return 'day_trader';
  });

  const [isReportsVisible, setIsReportsVisible] = useState(false);
  const [portfolio, setPortfolio] = useState<PortfolioEndpoint>({
    regular_trades: [],
    strategy_trades: []
  });
  const [loading, setLoading] = useState(true);

  // Replace dateFilter with date range state
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const now = new Date();
    const monday = startOfWeek(now, { weekStartsOn: 1 });
    const sunday = endOfWeek(now, { weekStartsOn: 1 });
    return {
      from: monday,
      to: sunday
    };
  });

  // Save configName to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('portfolioConfigName', configName);
  }, [configName]);

  const toggleReportsVisibility = () => {
    setIsReportsVisible(prev => !prev)
  }

  useEffect(() => {
    const fetchPortfolio = async () => {
      if (!dateRange?.from) return;
      
      setLoading(true);
      const filterOptions = {
        //weekFilter: dateRange.from.toISOString().split('T')[0],
        fromDate: dateRange.from.toISOString().split('T')[0],
        toDate: dateRange.to?.toISOString().split('T')[0]
      };
      
      try {
        const fetchedPortfolio = await getPortfolio({
          configName,
          ...filterOptions
        });
        setPortfolio(fetchedPortfolio);
      } catch (error) {
        console.error('Error fetching portfolio:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
  }, [configName, dateRange]);

  return (
    <main className="container mx-auto p-4 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <h1 className="text-3xl font-bold">Blue Deer Trading Dashboard</h1>
        </div>

        <div className="flex gap-4 items-center">
          <Select value={configName} onValueChange={setConfigName}>
            <SelectTrigger className="w-[180px]">
              <SelectValue>
                {TRADE_GROUPS.find(group => group.value === configName)?.label}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {TRADE_GROUPS.map((group) => (
                <SelectItem key={group.value} value={group.value}>
                  {group.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <DatePickerWithRange 
            date={dateRange}
            onDateChange={setDateRange}
          />

          <Button onClick={toggleReportsVisibility} variant="outline">
            {isReportsVisible ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
            {isReportsVisible ? "Hide Reports" : "Show Reports"}
          </Button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        <div className={`lg:${isReportsVisible ? 'w-2/3' : 'w-full'}`}>
          {loading ? (
            <p>Loading portfolio...</p>
          ) : (
            <PortfolioTableComponent portfolio={portfolio} />
          )}
        </div>
        {isReportsVisible && (
          <div className="lg:w-1/3">
            <ReportAreaComponent portfolio={portfolio} configName={configName} />
          </div>
        )}
      </div>
    </main>
  )
}
