import axios from 'axios';
import { PortfolioEndpoint, StrategyTrade, OptionsStrategyTrade } from '../utils/types';

const API_BASE_URL = 'http://localhost:8000'; // Update this with your API URL

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getTrades = async () => {
  try {
    const response = await api.get('/trades');
    return response.data;
  } catch (error) {
    console.error('Error fetching trades:', error);
    throw error;
  }
};

export const getTrade = async (tradeId: string) => {
  try {
    const response = await api.get(`/trades/${tradeId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching trade ${tradeId}:`, error);
    throw error;
  }
};

interface FilterOptions {
  status?: string;
  startDate?: string;
  endDate?: string;
  //timeFrame?: string;
  weekFilter?: string;
  monthFilter?: string;
  yearFilter?: string;
  optionType?: string;
}

export async function getTradesByConfiguration(configName: string, options: {
  status: string;
  weekFilter: string;
  optionType?: string;
  symbol?: string;
  tradeGroup?: string;
  minEntryPrice?: number;
  maxEntryPrice?: number;
  showAllTrades?: boolean;
}) {
  try {
    const queryParams = new URLSearchParams();

    if (configName !== "all") {
      queryParams.append('configName', configName);
    }
    
    if (options.status !== "all") {
      queryParams.append('status', options.status);
    }
    
    if (options.weekFilter) {
      queryParams.append('weekFilter', options.weekFilter);
    }
    
    // Only append optionType if it's defined
    if (options.optionType) {
      queryParams.append('optionType', options.optionType);
      console.log("Setting option_type to:", options.optionType);
    }
    
    if (options.symbol) {
      queryParams.append('symbol', options.symbol);
    }
    
    if (options.tradeGroup) {
      queryParams.append('configName', options.tradeGroup);
    }
    
    if (options.minEntryPrice) {
      queryParams.append('minEntryPrice', String(options.minEntryPrice));
    }
    
    if (options.maxEntryPrice) {
      queryParams.append('maxEntryPrice', String(options.maxEntryPrice));
    }
    
    if (options.showAllTrades) {
      queryParams.append('showAllTrades', String(options.showAllTrades));
    }

    console.log("API Request URL:", `/trades?${queryParams.toString()}`);
    const response = await api.get(`/trades?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching trades:', error);
    throw error;
  }
}

export async function getStrategyTradesByConfiguration(configName: string, filterOptions: FilterOptions): Promise<StrategyTrade[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('configName', configName);
  Object.entries(filterOptions).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, value);
    }
  });
  const response = await api.get(`/strategy_trades?${queryParams.toString()}`);
  return response.data;
}

export async function getPortfolio(configName: string, filterOptions: FilterOptions): Promise<PortfolioEndpoint> {
  const queryParams = new URLSearchParams();
  
  queryParams.append('configName', configName);
  Object.entries(filterOptions).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, value);
    }
  });

  const response = await api.get(`/portfolio?${queryParams.toString()}`);
  if (response.status !== 200) {
    throw new Error('Failed to fetch portfolio');
  }
  return response.data;
}

// Add a new function to handle data refresh
/*export const refreshData = async (configName: string, filterOptions: FilterOptions) => {
  try {
    const [tradesResponse, portfolioResponse] = await Promise.all([
      getTradesByConfiguration(configName, filterOptions),
      getPortfolio(configName, filterOptions)
    ]);
    
    return {
      trades: tradesResponse,
      portfolio: portfolioResponse
    };
  } catch (error) {
    console.error('Error refreshing data:', error);
    throw error;
  }
};*/

// Add more API functions as needed

export async function getOptionsStrategyTradesByConfiguration(
  configName: string,
  status: string,
  date?: string
): Promise<OptionsStrategyTrade[]> {
  const params = new URLSearchParams({
    config_name: configName,
    status: status,
    ...(date && { date: date }),
  });

  try {
    const response = await api.get(`/strategy_trades?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching options strategy trades:', error);
    throw new Error('Failed to fetch options strategy trades');
  }
}
