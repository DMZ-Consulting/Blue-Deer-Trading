import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getTrades = async () => {
  const response = await apiClient.get('/trades');
  return response.data;
};

export const getTrade = async (tradeId: string) => {
  const response = await apiClient.get(`/trades/${tradeId}`);
  return response.data;
};

export const getTradeConfigurations = async () => {
  const response = await apiClient.get('/trade-configurations');
  return response.data;
};

export default apiClient;
