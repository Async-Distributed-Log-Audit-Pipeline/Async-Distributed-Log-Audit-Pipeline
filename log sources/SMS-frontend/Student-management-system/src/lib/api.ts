// ─────────────────────────────────────────────────────────────────────────────
// Central API client
// Replace YOUR_API_BASE_URL with your actual backend URL, e.g.:
//   http://localhost:8080/api
// ─────────────────────────────────────────────────────────────────────────────
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:9191";

function getToken(): string | null {
    return localStorage.getItem("jwt_token");
}

function buildHeaders(extra?: Record<string, string>): HeadersInit {
    const token = getToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...extra,
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
        // Token expired or invalid – force logout
        localStorage.removeItem("jwt_token");
        window.location.href = "/login";
        throw new Error("Unauthorized");
    }
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP error ${response.status}`);
    }
    // Return null for 204 No Content
    if (response.status === 204) return null as T;
    return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: buildHeaders(),
    });
    return handleResponse<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: buildHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "PUT",
        headers: buildHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "DELETE",
        headers: buildHeaders(),
    });
    return handleResponse<T>(response);
}

export async function apiDownload(path: string, filename: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: buildHeaders({ Accept: "application/zip" }),
    });

    if (response.status === 401) {
        localStorage.removeItem("jwt_token");
        window.location.href = "/login";
        throw new Error("Unauthorized");
    }
    if (response.status === 404) {
        throw new Error("No runtime logs are available yet. Start the microservices and try again.");
    }
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP error ${response.status}`);
    }

    const downloadUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
}
