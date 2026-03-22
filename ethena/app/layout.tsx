import type { Metadata } from 'next'
import './globals.css'
import { Inter, Syne, DM_Mono } from 'next/font/google'
import NavWrapper from '@/components/NavWrapper'

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
        {/* Atmosphere Glow Orbs */}
        <div className="fixed top-[-10%] left-[-10%] w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none z-[-1]" />
        <div className="fixed bottom-[20%] right-[-10%] w-[400px] h-[400px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none z-[-1]" />
        <NavWrapper>
          <main className="min-h-screen overflow-x-hidden">
            {children}
          </main>
        </NavWrapper>
      </body>
    </html>
  )
}


