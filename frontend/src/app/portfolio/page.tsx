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
import { startOfWeek, endOfWeek, addDays, format, startOfMonth, endOfMonth, startOfQuarter, endOfQuarter, startOfYear, endOfYear, subDays, subWeeks, subMonths, subYears, isSameDay } from 'date-fns'

const TRADE_GROUPS = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" }
] as const;

// Preset options for date ranges
const PRESET_OPTIONS = [
  { label: 'Today', value: 'today' },
  { label: 'Last 7 days', value: 'last_7_days' },
  { label: 'Last 4 weeks', value: 'last_4_weeks' },
  { label: 'Last 3 months', value: 'last_3_months' },
  { label: 'Last 12 months', value: 'last_12_months' },
  { label: 'Month to date', value: 'month_to_date' },
  { label: 'Quarter to date', value: 'quarter_to_date' },
  { label: 'Year to date', value: 'year_to_date' },
];

function getPresetDateRange(preset: string): DateRange {
  const now = new Date();
  switch (preset) {
    case 'today':
      return { from: now, to: now };
    case 'last_7_days':
      return { from: subDays(now, 6), to: now };
    case 'last_4_weeks':
      return { from: subWeeks(now, 4), to: now };
    case 'last_3_months':
      return { from: subMonths(now, 3), to: now };
    case 'last_12_months':
      return { from: subMonths(now, 12), to: now };
    case 'month_to_date':
      return { from: startOfMonth(now), to: now };
    case 'quarter_to_date':
      return { from: startOfQuarter(now), to: now };
    case 'year_to_date':
      return { from: startOfYear(now), to: now };
    default:
      return { from: now, to: now };
  }
}

function getMatchingPreset(dateRange: DateRange): string | "" {
  for (const preset of PRESET_OPTIONS) {
    const presetRange = getPresetDateRange(preset.value);
    if (
      dateRange.from &&
      dateRange.to &&
      presetRange.from &&
      presetRange.to &&
      isSameDay(dateRange.from, presetRange.from) &&
      isSameDay(dateRange.to, presetRange.to)
    ) {
      return preset.value;
    }
  }
  return "";
}

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

  // Add timeFrameString state
  const [timeFrameString, setTimeFrameString] = useState<string>("");

  // Add preset state
  const [selectedPreset, setSelectedPreset] = useState<string>('last_7_days');

  // Update timeFrameString whenever dateRange changes
  useEffect(() => {
    if (dateRange?.from && dateRange?.to) {
      setTimeFrameString(`${format(dateRange.from, "LLL dd, y")} - ${format(dateRange.to, "LLL dd, y")}`);
    } else if (dateRange?.from) {
      setTimeFrameString(format(dateRange.from, "LLL dd, y"));
    } else {
      setTimeFrameString("");
    }
  }, [dateRange]);

  // Save configName to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('portfolioConfigName', configName);
  }, [configName]);

  // Update dateRange when preset changes
  useEffect(() => {
    if (selectedPreset) {
      setDateRange(getPresetDateRange(selectedPreset));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPreset]);

  // Handle date change from calendar
  const handleDateChange = (range: DateRange | undefined) => {
    setDateRange(range);
    if (range && range.from && range.to) {
      const matchingPreset = getMatchingPreset(range);
      setSelectedPreset(matchingPreset);
    } else {
      setSelectedPreset("");
    }
  };

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

          {/* Preset Dropdown */}
          <Select value={selectedPreset} onValueChange={setSelectedPreset}>
            <SelectTrigger className="w-[150px]">
              <SelectValue>{PRESET_OPTIONS.find(opt => opt.value === selectedPreset)?.label}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {PRESET_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <DatePickerWithRange 
            date={dateRange}
            onDateChange={handleDateChange}
            timeFrameString={timeFrameString}
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
            <div className="space-y-4 animate-pulse">
              <h2 className="h-8 w-40 bg-gray-200 rounded mb-2" />
              <div className="">
                <div className="bg-white border border-gray-200 rounded shadow-sm">
                  <div className="p-0">
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead>
                          <tr>
                            {[...Array(6)].map((_, i) => (
                              <th key={i} className="px-4 py-3">
                                <div className="h-5 bg-gray-200 rounded w-24 mx-auto" />
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[...Array(6)].map((_, rowIdx) => (
                            <tr key={rowIdx}>
                              {[...Array(6)].map((_, colIdx) => (
                                <td key={colIdx} className="px-4 py-2">
                                  <div className="h-4 bg-gray-200 rounded w-full" style={{ minWidth: '60px' }} />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <PortfolioTableComponent portfolio={portfolio} />
          )}
        </div>
        {isReportsVisible && (
          <div className="lg:w-1/3">
            <ReportAreaComponent portfolio={portfolio} configName={configName} timeFrameString={timeFrameString} />
          </div>
        )}
      </div>
    </main>
  )
}
