import { useEffect, useRef } from 'react';
import './DotMap.css';

// World map coordinates for dots (simplified representation)
const worldDots = [];
const mapWidth = 360;
const mapHeight = 180;
const dotSpacing = 4;

// Generate dot grid for landmasses (simplified)
for (let lat = -60; lat <= 70; lat += dotSpacing) {
  for (let lng = -180; lng <= 180; lng += dotSpacing) {
    // Simple landmass approximation
    if (isLand(lat, lng)) {
      worldDots.push({ lat, lng });
    }
  }
}

function isLand(lat, lng) {
  // North America
  if (lat > 25 && lat < 70 && lng > -170 && lng < -50) {
    if (lat > 50 && lng < -130) return true;
    if (lat > 25 && lat < 50 && lng > -130 && lng < -60) return true;
    return false;
  }
  // South America  
  if (lat > -55 && lat < 10 && lng > -80 && lng < -35) return true;
  // Europe
  if (lat > 35 && lat < 70 && lng > -10 && lng < 60) return true;
  // Africa
  if (lat > -35 && lat < 35 && lng > -20 && lng < 50) return true;
  // Asia
  if (lat > 5 && lat < 75 && lng > 60 && lng < 150) return true;
  // Australia
  if (lat > -45 && lat < -10 && lng > 110 && lng < 155) return true;
  // India
  if (lat > 5 && lat < 35 && lng > 68 && lng < 97) return true;
  
  return false;
}

const marketLocations = [
  { name: 'NIFTY 50', lat: 19.07, lng: 72.87, change: '+1.2%', positive: true },
  { name: 'S&P 500', lat: 40.71, lng: -74.00, change: '+0.8%', positive: true },
  { name: 'FTSE 100', lat: 51.50, lng: -0.12, change: '-0.3%', positive: false },
  { name: 'Nikkei 225', lat: 35.68, lng: 139.69, change: '+0.5%', positive: true },
  { name: 'DAX', lat: 50.11, lng: 8.68, change: '+0.2%', positive: true },
  { name: 'Hang Seng', lat: 22.32, lng: 114.17, change: '-0.4%', positive: false },
  { name: 'ASX 200', lat: -33.86, lng: 151.20, change: '+0.6%', positive: true },
  { name: 'Shanghai', lat: 31.23, lng: 121.47, change: '+0.3%', positive: true },
];

function DotMap() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth * 2;
    const height = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);

    const displayWidth = canvas.offsetWidth;
    const displayHeight = canvas.offsetHeight;

    // Clear
    ctx.clearRect(0, 0, displayWidth, displayHeight);

    // Draw dots
    worldDots.forEach(dot => {
      const x = ((dot.lng + 180) / 360) * displayWidth;
      const y = ((90 - dot.lat) / 180) * displayHeight;
      
      ctx.beginPath();
      ctx.arc(x, y, 1.2, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
      ctx.fill();
    });

    // Draw market locations
    marketLocations.forEach(market => {
      const x = ((market.lng + 180) / 360) * displayWidth;
      const y = ((90 - market.lat) / 180) * displayHeight;

      // Glow effect
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, 20);
      gradient.addColorStop(0, 'rgba(59, 130, 246, 0.6)');
      gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, 20, 0, Math.PI * 2);
      ctx.fill();

      // Center dot
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#3b82f6';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

  }, []);

  return (
    <div className="dot-map-container">
      <canvas ref={canvasRef} className="dot-map-canvas" />
      
      {/* Market Labels */}
      <div className="map-labels">
        {marketLocations.map((market, i) => {
          const left = ((market.lng + 180) / 360) * 100;
          const top = ((90 - market.lat) / 180) * 100;
          
          return (
            <div 
              key={i}
              className="map-label"
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <div className="label-pin">
                <div className="pin-dot"></div>
              </div>
              <div className="label-card">
                <span className="label-name">{market.name}</span>
                <span className={`label-change ${market.positive ? 'positive' : 'negative'}`}>
                  {market.change}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DotMap;
