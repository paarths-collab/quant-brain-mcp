'use client'

import { usePathname } from 'next/navigation'
import Navbar from './Navbar'
import Footer from './Footer'

export default function NavWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  
  // Define routes where we want to hide the landing page Navbar and Footer
  const hideNavFooter = 
    pathname.startsWith('/dashboard') || 
    pathname.startsWith('/technical') || 
    pathname.startsWith('/markets') || 
    pathname.startsWith('/sectors') || 
    pathname.startsWith('/research') || 
    pathname.startsWith('/backtest') ||
    pathname.startsWith('/chat') ||
    pathname.startsWith('/portfolio') ||
    pathname.startsWith('/sector') // keep the existing sector hide logic

  return (
    <>
      {!hideNavFooter && <Navbar />}
      {children}
      {!hideNavFooter && <Footer />}
    </>
  )
}
