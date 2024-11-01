import axios from 'axios';
import { Trade, PortfolioEndpoint } from '../utils/types';

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
}

export async function getTradesByConfiguration(configName: string, filterOptions: FilterOptions): Promise<Trade[]> {
  const queryParams = new URLSearchParams();
  
  queryParams.append('configName', configName);
  
  Object.entries(filterOptions).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, value);
    }
  });

  try {
    const response = await api.get(`/trades?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching trades:', error);
    throw new Error('Failed to fetch trades');
  }
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

// Add more API functions as needed
