'use client'

import { usePathname } from 'next/navigation'
import Navbar from './Navbar'
import Footer from './Footer'
import TerminalLayout from './TerminalLayout'

export default function NavWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  const terminalRoutes = [
    '/dashboard',
    '/technical',
    '/markets',
    '/sectors',
    '/research',
    '/backtest',
    '/chat',
    '/portfolio',
    '/profile',
    '/settings',
  ]

  const isTerminalRoute = terminalRoutes.some((route) => pathname.startsWith(route))

  // Define routes where we want to hide the landing page Navbar and Footer
  const hideNavFooter =
    isTerminalRoute ||
    pathname.startsWith('/sector')

  return (
    <>
      {!hideNavFooter && <Navbar />}
      {isTerminalRoute ? (
        <TerminalLayout>{children}</TerminalLayout>
      ) : (
        children
      )}
      {!hideNavFooter && <Footer />}
    </>
  )
}
