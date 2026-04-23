import axios from "axios";

const rawApiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const API_BASE = rawApiBase.endsWith("/") ? rawApiBase.slice(0, -1) : rawApiBase;
const ADMIN_TOKEN_KEY = "auction_admin_token";
const API = axios.create({
  baseURL: `${API_BASE}/api/`,
});

const getStoredAdminToken = () => localStorage.getItem(ADMIN_TOKEN_KEY);

API.interceptors.request.use((config) => {
  const token = getStoredAdminToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export const setAdminToken = (token) => {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
};

export const clearAdminToken = () => {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
};

export const hasAdminToken = () => Boolean(getStoredAdminToken());

export const adminLogin = (payload) => API.post("auth/login/", payload);
export const adminMe = () => API.get("auth/me/");
export const adminLogout = () => API.post("auth/logout/");

export const getPlayers = () => API.get("players/");
export const createPlayer = (formData) =>
  API.post("players/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const getCurrentAuction = () => axios.get(`${API_BASE}/current-auction/`);

export const setAuctionPlayer = (auctionId, playerId) =>
  API.post(`auction/${auctionId}/set_player/`, { player_id: playerId });

export const sellCurrentPlayer = (auctionId, payload) =>
  API.post(`auction/${auctionId}/sell_player/`, payload);

export const skipCurrentPlayer = (auctionId) =>
  API.post(`auction/${auctionId}/skip_player/`);

export const resolveImageUrl = (player) => {
  if (!player) {
    return "";
  }

  const source = player.image_url || player.image || "";
  if (!source) {
    return "";
  }
  if (source.startsWith("http://") || source.startsWith("https://")) {
    return source;
  }
  return `${API_BASE}${source}`;
};
