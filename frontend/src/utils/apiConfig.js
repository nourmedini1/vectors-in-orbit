// Helper to expose backend base URLs from Vite env variables.
// Expectation: set VITE_MONGO_API and VITE_SEARCH_API to host:port (e.g. 192.168.1.128:8000)
// Both can also include the protocol (http:// or https://). If protocol is omitted, http:// is prefixed.
const getEnv = (name, defaultUrl) => {
  const raw = import.meta.env[`VITE_${name}`] || '';
  const val = raw || defaultUrl;
  if (!val) return val;
  return (val.startsWith('http://') || val.startsWith('https://')) ? val : `http://${val}`;
};

export const MONGO_API = getEnv('MONGO_API', 'http://localhost:8000');
export const SEARCH_API = getEnv('SEARCH_API', 'http://localhost:8002');
