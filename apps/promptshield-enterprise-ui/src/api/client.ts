import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
const apiKey = import.meta.env.VITE_API_KEY || ''

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
  },
  timeout: 15_000,
})

// Add response error interceptor for unified error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication error: check your API key in Settings')
    }
    return Promise.reject(error)
  },
)

// Admin client with admin API key (same host, different key for admin endpoints)
const adminKey = import.meta.env.VITE_ADMIN_KEY || apiKey

export const adminClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': adminKey,
  },
  timeout: 15_000,
})
