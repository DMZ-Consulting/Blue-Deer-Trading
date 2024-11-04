'use client'

import { useState, useEffect } from 'react'
import { PortfolioTableComponent } from '@/components/PortfolioTable'
import { ReportAreaComponent } from '@/components/ReportArea'
import { Button } from "@/components/ui/button"
import { PanelRightOpen, PanelRightClose } from 'lucide-react'
import { getPortfolio } from '@/api/api'
import { PortfolioTrade } from '@/utils/types'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"

const TRADE_GROUPS = [
  { value: "day_trader", label: "Day Trader" },
  { value: "swing_trader", label: "Swing Trader" },
  { value: "long_term_trader", label: "Long Term Trader" }
] as const;

export default function PortfolioPage() {
  const [configName, setConfigName] = useState('day_trader')
  const [isReportsVisible, setIsReportsVisible] = useState(true)
  const [portfolio, setPortfolio] = useState<PortfolioTrade[]>([])
  const [loading, setLoading] = useState(true)
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date();
    // Get the Monday of the current week
    const monday = new Date(now);
    monday.setDate(now.getDate() - now.getDay() + 1);
    return monday.toISOString().split('T')[0];
  });

  const toggleReportsVisibility = () => {
    setIsReportsVisible(prev => !prev)
  }

  useEffect(() => {
    const fetchPortfolio = async () => {
      setLoading(true)
      const filterOptions = {
        weekFilter: dateFilter,
      }
      try {
        const fetchedPortfolio = await getPortfolio(configName, filterOptions)
        setPortfolio(fetchedPortfolio)
      } catch (error) {
        console.error('Error fetching portfolio:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPortfolio()
  }, [configName, dateFilter])

  const handleDateChange = (newDate: string) => {
    // Convert the selected date to the Monday of that week
    const selectedDate = new Date(newDate);
    const monday = new Date(selectedDate);
    monday.setDate(selectedDate.getDate() - selectedDate.getDay() + 1);
    setDateFilter(monday.toISOString().split('T')[0]);
  }

  // Generate week options for the last 12 weeks
  const getWeekOptions = () => {
    const options = [];
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() - today.getDay() + 1);

    for (let i = 0; i < 12; i++) {
      const date = new Date(monday);
      date.setDate(monday.getDate() - (7 * i));
      const friday = new Date(date);
      friday.setDate(date.getDate() + 4);

      options.push({
        value: date.toISOString().split('T')[0],
        label: `Week of ${friday.toLocaleDateString()}`
      });
    }
    return options;
  }

  // Get the label for the current selected date
  const getSelectedWeekLabel = () => {
    const selectedDate = new Date(dateFilter);
    const friday = new Date(selectedDate);
    friday.setDate(selectedDate.getDate() + 4); // Get to Friday from Monday
    return `Week of ${friday.toLocaleDateString()}`;
  }

  return (
    <div id="portfolio-page" className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Blue Deer Trading Dashboard</h1>
        <Button onClick={toggleReportsVisibility} variant="outline">
          {isReportsVisible ? <PanelRightClose className="w-4 h-4 mr-2" /> : <PanelRightOpen className="w-4 h-4 mr-2" />}
          {isReportsVisible ? "Hide Reports" : "Show Reports"}
        </Button>
      </div>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className={`lg:${isReportsVisible ? 'w-2/3' : 'w-full'}`}>
          <Card className="mb-4">
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4 items-center">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Trade Group</label>
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
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Week</label>
                  <Select value={dateFilter} onValueChange={handleDateChange}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue>
                        {getSelectedWeekLabel()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {getWeekOptions().map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {loading ? (
            <p>Loading portfolio...</p>
          ) : (
            <PortfolioTableComponent portfolio={portfolio} />
          )}
        </div>
        {isReportsVisible && (
          <div className="lg:w-1/3">
            <ReportAreaComponent portfolio={portfolio} />
          </div>
        )}
      </div>
    </div>
  )
}
