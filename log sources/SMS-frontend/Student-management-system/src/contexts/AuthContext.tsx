import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { API_BASE_URL } from "@/lib/api";

interface AuthContextType {
  isAuthenticated: boolean;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("jwt_token")
  );

  const isAuthenticated = !!token;

  const login = useCallback(async (username: string, password: string) => {
    // POST YOUR_API_BASE_URL/auth/login
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const msg = await response.text();
      throw new Error(msg || "Invalid credentials");
    }

    const data = await response.json();
    // Adjust "token" key to match your backend's response field, e.g. data.accessToken
    const jwt: string = data.token ?? data.accessToken ?? data.jwt;
    if (!jwt) throw new Error("No token received from server");

    localStorage.setItem("jwt_token", jwt);
    setToken(jwt);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("jwt_token");
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}