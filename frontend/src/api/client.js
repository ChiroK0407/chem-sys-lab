import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "https://chem-sys-lab.onrender.com",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Unwrap FastAPI error detail into a clean Error object
client.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail;
    if (detail && typeof detail === "object") {
      return Promise.reject(
        new Error(`${detail.error_type}: ${detail.message}`)
      );
    }
    if (detail && typeof detail === "string") {
      return Promise.reject(new Error(detail));
    }
    return Promise.reject(err);
  }
);

export default client;
