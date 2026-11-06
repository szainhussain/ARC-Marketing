import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import './styles/components.css'
import { ToastProvider } from './components/ui'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext'
import { WorkspaceProvider } from './context/WorkspaceContext'
import { ThemeProvider } from './context/ThemeContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <WorkspaceProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </WorkspaceProvider>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)
