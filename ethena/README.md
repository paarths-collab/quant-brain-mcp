# Ethena — Next.js Replica

Production-grade Next.js 14 replica of the Ethena website with full glassmorphism UI and Framer Motion animations.

## Stack
- **Next.js 14** — App Router
- **TypeScript**
- **Tailwind CSS** — Dark glassmorphism design system
- **Framer Motion** — Scroll reveals, hover physics, stagger animations
- **Lucide React** — Professional icons

## Pages
- `/` — Homepage: Hero + 3D Globe + Stats + APY Bars + Onboarding Cards + Transparency Bento + CTA
- `/ecosystem` — Protocol grid with live filter tabs (All / DEXs / Money Markets / Exchanges / Derivatives / Yield / Stablecoins)
- `/network` — OES architecture diagram + Custodian partner carousel
- `/blog` — Featured article + Research grid

## Setup

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Build for production

```bash
npm run build
npm start
```

## File Structure

```
ethena/
├── app/
│   ├── layout.tsx          # Root layout: Navbar, Footer, ambient glows
│   ├── globals.css         # Design tokens, glass utilities, animations
│   ├── page.tsx            # Homepage
│   ├── ecosystem/page.tsx  # Ecosystem filter grid
│   ├── network/page.tsx    # Network + custodians
│   └── blog/page.tsx       # Blog listing
├── components/
│   ├── Navbar.tsx          # Fixed glass nav with ENA price ticker
│   ├── Footer.tsx          # Multi-column footer
│   ├── Globe.tsx           # Canvas WebGL-style rotating globe
│   ├── MotionComponents.tsx # FadeIn, GlassCard, StaggerContainer, StaggerItem
│   └── SectionLabel.tsx    # Monospace label badge
└── lib/
    └── data.ts             # All static data arrays
```

## Design System

| Token | Value |
|-------|-------|
| Background | `#050507` |
| Surface | `#0d0d10` |
| Accent | `#6366f1` (indigo) |
| Accent2 | `#818cf8` |
| Green | `#4ade80` |
| Font Heading | Syne |
| Font Body | DM Sans |
| Font Mono | DM Mono |

## Key Techniques

- **Glassmorphism**: `bg-[#0d0d10]/70 backdrop-blur-xl border border-white/[0.07]`
- **Globe**: Canvas API + Fibonacci sphere + auto-rotation
- **Scroll Reveals**: Framer Motion `whileInView` with `once: true`
- **Stagger**: `StaggerContainer` + `StaggerItem` variants
- **Hover Physics**: `whileHover={{ y: -4 }}` on all cards
- **Ambient Glows**: Fixed, blurred, colored `div` orbs
