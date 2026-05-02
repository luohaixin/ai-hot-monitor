import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { motion } from 'framer-motion'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Hotspots from './pages/Hotspots'
import Keywords from './pages/Keywords'
import Search from './pages/Search'
import Settings from './pages/Settings'
import { WebSocketProvider } from './hooks/useWebSocket'
import './styles/App.css'

function App() {
  return (
    <WebSocketProvider>
      <Router>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="min-h-screen bg-gray-50 dark:bg-gray-900"
        >
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/hotspots" element={<Hotspots />} />
              <Route path="/keywords" element={<Keywords />} />
              <Route path="/search" element={<Search />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </motion.div>
      </Router>
    </WebSocketProvider>
  )
}

export default App
