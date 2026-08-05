import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AnalysePage } from './pages/AnalysePage'
import { ArchitecturePage } from './pages/ArchitecturePage'
import { HistoryPage } from './pages/HistoryPage'
import { ReliabilityPage } from './pages/ReliabilityPage'

const router = createBrowserRouter([
  { path: '/', element: <Layout />, children: [
    { index: true, element: <AnalysePage /> },
    { path: 'history', element: <HistoryPage /> },
    { path: 'reliability', element: <ReliabilityPage /> },
    { path: 'architecture', element: <ArchitecturePage /> },
  ] },
])

export default function App() { return <RouterProvider router={router} /> }
