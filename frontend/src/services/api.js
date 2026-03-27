import axios from "axios";

export const AUTH_TOKEN_KEY = "finance_auth_token";
export const AUTH_USER_KEY = "finance_auth_user";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fetchDashboard = async () => {
  const response = await api.get("/dashboard");
  return response.data;
};

export const fetchTransactions = async () => {
  const response = await api.get("/transactions");
  return response.data;
};

export const uploadStatement = async (file, bankName, onUploadProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("bank_name", bankName);
  const response = await api.post("/upload-statement", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return response.data;
};

export const askFinanceAssistant = async (query, mode) => {
  const response = await api.post("/chat", { query, mode });
  return response.data;
};

export const resetFinancialData = async () => {
  const response = await api.delete("/reset-data");
  return response.data;
};

export const updateTransactionType = async (transactionId, transactionType) => {
  const response = await api.patch("/update-transaction-type", {
    transactionId,
    transactionType,
  });
  return response.data;
};

export const updateTransactionCategory = async (transactionId, category) => {
  const response = await api.patch("/update-transaction-category", {
    transactionId,
    category,
  });
  return response.data;
};

export const createNonBankingTransaction = async (payload) => {
  const response = await api.post("/non-banking-transactions", payload);
  return response.data;
};

export const registerUser = async (payload) => {
  const response = await api.post("/auth/register", payload);
  return response.data;
};

export const loginUser = async (payload) => {
  const response = await api.post("/auth/login", payload);
  return response.data;
};

export const fetchCurrentUser = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const logoutUser = async () => {
  const response = await api.post("/auth/logout");
  return response.data;
};

// Loans API
export const fetchLoans = async () => {
  const response = await api.get("/loans");
  return response.data;
};

export const createLoan = async (payload) => {
  const response = await api.post("/loans", payload);
  return response.data;
};

export const updateLoan = async (loanId, payload) => {
  const response = await api.patch(`/loans/${loanId}`, payload);
  return response.data;
};

export const deleteLoan = async (loanId) => {
  const response = await api.delete(`/loans/${loanId}`);
  return response.data;
};

export default api;

export const getFriendlyApiError = (error, fallbackMessage) => {
  const detail = error?.response?.data?.detail || error?.response?.data?.warning || error?.message || "";
  if (detail && /limit|quota|rate/i.test(detail)) {
    return "API call limit reached, change the api key.";
  }
  if (error?.response?.status === 401) {
    return "Your session has expired. Please log in again.";
  }
  return detail || fallbackMessage;
};
