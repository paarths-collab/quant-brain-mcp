import type { Metadata } from 'next'
import './globals.css'
import { Inter, Syne, DM_Mono } from 'next/font/google'
import NavWrapper from '@/components/NavWrapper'
import GlobalPageAnalyzer from '@/components/GlobalPageAnalyzer'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const syne = Syne({ subsets: ['latin'], variable: '--font-syne' })
const dmMono = DM_Mono({ weight: ['400', '500'], subsets: ['latin'], variable: '--font-mono' })

export const metadata: Metadata = {
  title: 'Bloomberg Quant — Intelligent Quantitative Finance',
  description: 'Orchestrating a decentralized committee of AI Agents and institutional-grade mathematics to deliver explainable alpha.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${syne.variable} ${dmMono.variable}`}>
      <body className="bg-background text-white selection:bg-accent/30 overflow-x-hidden font-inter">
        <NavWrapper>
          <div className="min-h-screen overflow-x-hidden page-shine-shell">
            <div className="page-shine-veil" aria-hidden />
            {children}
          </div>
        </NavWrapper>
        <GlobalPageAnalyzer />
      </body>
    </html>
  )
}


