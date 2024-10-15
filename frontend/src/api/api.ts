import axios from 'axios';

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
export const getTradesByConfiguration = async (configName: string, status?: string) => {
  try {
    const params = new URLSearchParams();
    params.append('config', configName);
    if (status) params.append('status', status);
    const response = await api.get(`/trades?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching trades for configuration ${configName}:`, error);
    throw error;
  }
};

// Add more API functions as needed
