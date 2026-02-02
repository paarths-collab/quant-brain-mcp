"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Search, Globe, ArrowRight } from "lucide-react";
import useSound from "use-sound";
import { HOVER_SOUND, CLICK_SOUND } from "@/utils/sounds";

// Dynamically import FinanceGlobe with no SSR to avoid window is not defined
const FinanceGlobe = dynamic(() => import("@/components/FinanceGlobe"), { ssr: false });

export default function Home() {
  const [playHover] = useSound(HOVER_SOUND, { volume: 0.2 });
  const [playClick] = useSound(CLICK_SOUND, { volume: 0.5 });

  return (
    <main className="relative w-full h-screen overflow-hidden bg-black text-white selection:bg-blue-500 selection:text-white">
      {/* 3D Background */}
      <FinanceGlobe />

      {/* Overlay UI */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none p-4">

        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="text-center pointer-events-auto max-w-4xl mx-auto"
        >
          <div className="mb-6 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-sm text-blue-200">
            <Globe className="w-4 h-4" />
            <span>Global Finance Explorer</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-white/50 pb-2">
            Boomerang
          </h1>

          <p className="text-lg md:text-xl text-blue-100/80 max-w-2xl mx-auto mb-10 font-light px-4">
            Navigate the complexity of global markets with precision AI.
          </p>

          {/* Search / Entry Bar */}
          <div className="relative group max-w-md mx-auto w-full px-4 md:px-0">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-lg blur opacity-25 group-hover:opacity-75 transition duration-1000 group-hover:duration-200"></div>
            <div className="relative flex items-center bg-black/50 backdrop-blur-xl border border-white/10 rounded-lg px-4 py-3 shadow-2xl">
              <Search className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" />
              <input
                type="text"
                placeholder="Search assets..."
                className="bg-transparent border-none outline-none text-white w-full placeholder-gray-500 min-w-0"
                onMouseEnter={() => playHover()}
              />
              <button
                onClick={() => playClick()}
                className="ml-2 p-2 rounded-md bg-white/10 hover:bg-white/20 transition-colors text-white flex-shrink-0"
              >
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Footer Info */}
      <div className="absolute bottom-10 left-0 w-full text-center text-xs text-white/30 z-10 px-4">
        <p>Real-time Data • AI Powered • Institutional Grade</p>
      </div>
    </main>
  );
}
