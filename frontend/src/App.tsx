import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import {
  Dashboard,
  Scans,
  ScanDetail,
  Findings,
  FindingDetail,
  Clusters,
  ClusterDetail,
  Patterns,
} from './pages'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scans" element={<Scans />} />
          <Route path="/scans/:id" element={<ScanDetail />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/findings/:id" element={<FindingDetail />} />
          <Route path="/clusters" element={<Clusters />} />
          <Route path="/clusters/:id" element={<ClusterDetail />} />
          <Route path="/patterns" element={<Patterns />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
