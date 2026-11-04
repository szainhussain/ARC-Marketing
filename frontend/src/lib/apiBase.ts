/**
 * Where the browser sends API calls.
 *
 * Production: same-origin `/api/v1`. Vercel forwards it to the backend
 * (see frontend/vercel.json), so session cookies are first-party and work
 * in Safari, which blocks cross-site cookies.
 * Development: VITE_API_BASE_URL (frontend/.env.local), e.g.
 * http://localhost:5000/api/v1.
 */
export const API_BASE_URL: string = import.meta.env.PROD
  ? '/api/v1'
  : import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'
