'use client'

import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

interface Point {
  x: number; y: number; z: number;
  s: number; alpha: number; major: boolean;
}

let globalPointsCache: Point[] | null = null;

export default function ContinentGlobe() {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const isInView = useInView(containerRef, { margin: "200px" })
  
  const [points, setPoints] = useState<Point[]>(globalPointsCache || [])
  const rotationY = useRef(0)
  const rafRef = useRef<number>()

  // 1. ONE-TIME IMAGE LOADING / CACHE RESTORAL
  useEffect(() => {
    if (globalPointsCache) return; // Already loaded globally

    const loadImg = (src: string) => new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = src
    })

    const initGlobe = async () => {
      try {
        // Load the reliable original map which is a binary land mask
        const map = await loadImg("/world-map.jpg")
        
        const tempCanvas = document.createElement('canvas')
        const tCtx = tempCanvas.getContext('2d')
        const mapW = 1000, mapH = 500
        tempCanvas.width = mapW
        tempCanvas.height = mapH
        
        tCtx?.drawImage(map, 0, 0, mapW, mapH)
        const imageData = tCtx?.getImageData(0, 0, mapW, mapH).data
        if (!imageData) return

        const newPoints: Point[] = []
        // Reduced density for smoother frame-time
        for (let y = 0; y < mapH; y += 6.5) {
          for (let x = 0; x < mapW; x += 6.5) {
            const pixelIndex = (Math.floor(y) * mapW + Math.floor(x)) * 4
            
            // In the original map: Continents are BLACK (<100), Oceans are WHITE (>120)
            if (imageData[pixelIndex] < 100) { 
              const phi = (y / mapH) * Math.PI
              const theta = (x / mapW) * 2 * Math.PI
              newPoints.push({
                x: -220 * Math.sin(phi) * Math.cos(theta),
                y: -220 * Math.cos(phi),
                z: 220 * Math.sin(phi) * Math.sin(theta),
                s: Math.random() * 1.1 + 0.4,
                alpha: Math.random() * 0.4 + 0.6,
                major: Math.random() > 0.985
              })
            }
          }
        }
        // Sequential loading to prevent lag
        const batchSize = 150
        let currentIdx = 0
        
        const loadBatch = () => {
          if (currentIdx >= newPoints.length) return
          
          const end = Math.min(currentIdx + batchSize, newPoints.length)
          const batch = newPoints.slice(currentIdx, end)
          
          setPoints(prev => [...prev, ...batch])
          currentIdx = end
          
          if (currentIdx >= newPoints.length) {
            globalPointsCache = newPoints
          } else {
            requestAnimationFrame(loadBatch)
          }
        }
        
        loadBatch()
      } catch (err) {
        console.error("Failed to load map asset for globe.", err)
      }
    }

    initGlobe()
  }, []) // Depend only on mount

  // 2. HIGH-PERFORMANCE VISIBILITY-TRIGGERED LOOP
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || points.length === 0 || !isInView) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    // Cap DPR at 1.5 as per Best Practice guide
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    // Sized to exactly 640px as per Best Practice guide
    const size = 640
    const W = size, H = size, R = 220
    canvas.width = size * dpr
    canvas.height = size * dpr
    ctx.scale(dpr, dpr)

    const projected: any[] = []
    const FPS = 30
    const frameInterval = 1000 / FPS
    let lastTime = 0

    const render = (time = 0) => {
      if (document.hidden) {
        rafRef.current = requestAnimationFrame(render)
        return
      }
      if (time - lastTime < frameInterval) {
        rafRef.current = requestAnimationFrame(render)
        return
      }
      lastTime = time

      ctx.clearRect(0, 0, W, H)
      rotationY.current += 0.0035

      for (let i = 0; i < points.length; i++) {
        const p = points[i]
        // Standard Y-axis orbital rotation
        const x = p.x * Math.cos(rotationY.current) - p.z * Math.sin(rotationY.current)
        const z = p.x * Math.sin(rotationY.current) + p.z * Math.cos(rotationY.current)
        const perspective = 900 / (900 - z)
        
        if (!projected[i]) projected[i] = { px: 0, py: 0, z: 0, s: 0, a: 0, major: false }
        projected[i].px = x * perspective + W/2
        projected[i].py = p.y * perspective + H/2
        projected[i].z = z
        projected[i].s = p.s * perspective
        projected[i].a = p.alpha
        projected[i].major = p.major
      }

      ctx.fillStyle = "#ffffff"
      for (let i = 0; i < projected.length; i++) {
        const p = projected[i]
        const zAlpha = (p.z + R) / (2 * R)
        if (zAlpha < 0.1) continue
        const opacity = Math.pow(zAlpha, 3) * p.a
        
        const dx = p.px - W/2
        const dy = p.py - H/2
        const isRim = (dx*dx + dy*dy) > R * R * 0.77 

        ctx.beginPath()
        ctx.arc(p.px, p.py, p.major ? p.s * 1.8 : p.s, 0, Math.PI * 2)
        
        if (isRim && p.z > 0) {
          ctx.globalAlpha = opacity + 0.2
          ctx.fillStyle = "#b4d2ff"
          ctx.fill()
          ctx.fillStyle = "#ffffff"
        } else if (p.major && p.z > 0) {
          ctx.globalAlpha = opacity + 0.3
          ctx.fill()
        } else {
          ctx.globalAlpha = opacity * 0.7
          ctx.fill()
        }
      }

      rafRef.current = requestAnimationFrame(render)
    }

    render()

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [points, isInView])

  return (
    <div 
      ref={containerRef}
      className="relative w-[640px] h-[640px] flex items-center justify-center pointer-events-none"
    >
      <div className="absolute inset-0 bg-indigo-600/15 rounded-full blur-[120px] scale-75" />
      
      {/* Standardized Animation Classes from Replication Guide */}
      <div className="absolute inset-0 rounded-full border border-white/5 animate-spin-60s" />
      <div className="absolute inset-[-40px] rounded-full border border-white/[0.03] animate-spin-100s-reverse" />
      <div className="absolute inset-[-80px] rounded-full border border-white/[0.01] animate-spin-140s" />

        <canvas
          ref={canvasRef}
          className="relative z-10 will-change-transform"
          style={{ width: '640px', height: '640px' }}
        />
      
      <div className="absolute top-[12%] left-1/2 -translate-x-1/2 w-[300px] h-[1px] bg-gradient-to-r from-transparent via-indigo-400/20 to-transparent blur-[10px]" />
    </div>
  )
}
