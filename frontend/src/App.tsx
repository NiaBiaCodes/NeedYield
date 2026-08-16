import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { FindFoodPage } from './pages/FindFoodPage'
import { ReservationsPage } from './pages/ReservationsPage'
import { AboutPage } from './pages/AboutPage'
import { DonatePage } from './pages/DonatePage'
import { AuthProvider } from './context/AuthContext'
import { AuthPage } from './pages/AuthPage'
import { AccountPage } from './pages/AccountPage'
import { DonationsPage } from './pages/DonationsPage'
import { AssistantPage } from './pages/AssistantPage'
import { OrganizationPage } from './pages/OrganizationPage'
import { AdminOrganizationsPage } from './pages/AdminOrganizationsPage'

export default function App() {
  return <BrowserRouter><AuthProvider><AppProvider><Layout><Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/find-food" element={<FindFoodPage />} />
    <Route path="/reservations" element={<ReservationsPage />} />
    <Route path="/donate" element={<DonatePage />} />
    <Route path="/donations" element={<DonationsPage />} />
    <Route path="/auth" element={<AuthPage />} />
    <Route path="/account" element={<AccountPage />} />
    <Route path="/assistant" element={<AssistantPage />} />
    <Route path="/organization" element={<OrganizationPage />} />
    <Route path="/admin/organizations" element={<AdminOrganizationsPage />} />
    <Route path="/about" element={<AboutPage />} />
    <Route path="*" element={<HomePage />} />
  </Routes></Layout></AppProvider></AuthProvider></BrowserRouter>
}
