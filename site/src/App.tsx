import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import AppPage from '@/pages/AppPage'
import Docs from '@/pages/Docs'
import Features from '@/pages/Features'
import GetStarted from '@/pages/GetStarted'
import Home from '@/pages/Home'
import HowItWorks from '@/pages/HowItWorks'
import Security from '@/pages/Security'
import { About, Contact, FaqPage, NotFound, Privacy, Terms } from '@/pages/Simple'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="app" element={<AppPage />} />
          <Route path="features" element={<Features />} />
          <Route path="how-it-works" element={<HowItWorks />} />
          <Route path="security" element={<Security />} />
          <Route path="docs" element={<Docs />} />
          <Route path="get-started" element={<GetStarted />} />
          <Route path="faq" element={<FaqPage />} />
          <Route path="about" element={<About />} />
          <Route path="contact" element={<Contact />} />
          <Route path="privacy" element={<Privacy />} />
          <Route path="terms" element={<Terms />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
