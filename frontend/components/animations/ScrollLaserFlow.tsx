'use client';

import React from 'react';
import { useScroll, useTransform, useSpring } from 'framer-motion';
import { LaserFlow } from './LaserFlow';

interface ScrollLaserFlowProps {
  className?: string;
  color?: string;
}

export const ScrollLaserFlow: React.FC<ScrollLaserFlowProps> = ({ 
  className,
  color = '#4f46e5' 
}) => {
  const { scrollYProgress } = useScroll();
  
  // Smooth out the scroll progress
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  // Map scroll progress (0 to 1) to LaserFlow properties
  // "as we scroll down the light brights"
  const fogIntensity = useTransform(smoothProgress, [0, 1], [0.35, 0.85]);
  const wispIntensity = useTransform(smoothProgress, [0, 1], [4.0, 12.0]);
  const flowSpeed = useTransform(smoothProgress, [0, 1], [0.25, 0.75]);
  const flowStrength = useTransform(smoothProgress, [0, 1], [0.2, 0.5]);

  return (
    <div className={`fixed inset-0 pointer-events-none z-0 ${className || ''}`}>
      <LaserFlow
        color={color}
        fogIntensity={fogIntensity.get()}
        wispIntensity={wispIntensity.get()}
        flowSpeed={flowSpeed.get()}
        flowStrength={flowStrength.get()}
        mouseTiltStrength={0.02}
        wispDensity={1.2}
      />
    </div>
  );
};

export default ScrollLaserFlow;
