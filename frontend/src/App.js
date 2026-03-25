import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import ChatbotPage from "./pages/ChatbotPage";
import FinanceDashboardPage from "./pages/FinanceDashboardPage";
import TransactionsPage from "./pages/TransactionsPage";

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <FinanceDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chatbot"
          element={
            <ProtectedRoute>
              <ChatbotPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/transactions"
          element={
            <ProtectedRoute>
              <TransactionsPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/auth"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
