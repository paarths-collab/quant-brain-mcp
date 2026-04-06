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
    '/sector',
    '/peers',
    '/peer',
    '/news',
    '/network',
    '/research',
    '/backtest',
    '/chat',
    '/portfolio',
    '/profile',
    '/settings',
  ]

  const isTerminalRoute = terminalRoutes.some((route) => pathname.startsWith(route))
  const isHomePage = pathname === '/'

  // Show landing chrome only on the main front page.
  const showLandingChrome = isHomePage

  return (
    <>
      {showLandingChrome && <Navbar />}
      {isTerminalRoute ? (
        <TerminalLayout>{children}</TerminalLayout>
      ) : (
        children
      )}
      {showLandingChrome && <Footer />}
    </>
  )
}
