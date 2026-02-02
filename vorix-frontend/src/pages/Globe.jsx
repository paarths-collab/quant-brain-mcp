import { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Html } from '@react-three/drei';
import { Activity, TrendingUp, TrendingDown, Globe as GlobeIcon } from 'lucide-react';
import './Globe.css';

// Market data points on globe
const marketData = [
  { name: 'New York', lat: 40.7128, lng: -74.0060, value: '+1.24%', positive: true },
  { name: 'London', lat: 51.5074, lng: -0.1278, value: '+0.89%', positive: true },
  { name: 'Tokyo', lat: 35.6762, lng: 139.6503, value: '-0.32%', positive: false },
  { name: 'Hong Kong', lat: 22.3193, lng: 114.1694, value: '+0.56%', positive: true },
  { name: 'Sydney', lat: -33.8688, lng: 151.2093, value: '+0.78%', positive: true },
  { name: 'Frankfurt', lat: 50.1109, lng: 8.6821, value: '-0.15%', positive: false },
  { name: 'Singapore', lat: 1.3521, lng: 103.8198, value: '+0.45%', positive: true },
  { name: 'Mumbai', lat: 19.0760, lng: 72.8777, value: '+1.02%', positive: true },
];

// Convert lat/lng to 3D coordinates
function latLngToVector3(lat, lng, radius) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  
  return [x, y, z];
}

function GlobeMesh({ onSelectMarket }) {
  const meshRef = useRef();
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.001;
    }
  });

  return (
    <group ref={meshRef}>
      {/* Earth sphere */}
      <Sphere args={[2, 64, 64]}>
        <meshStandardMaterial 
          color="#1a1a2e"
          wireframe
          transparent
          opacity={0.3}
        />
      </Sphere>
      
      {/* Inner glow */}
      <Sphere args={[1.98, 32, 32]}>
        <meshStandardMaterial 
          color="#7c3aed"
          transparent
          opacity={0.1}
        />
      </Sphere>

      {/* Market points */}
      {marketData.map((market, i) => {
        const position = latLngToVector3(market.lat, market.lng, 2.05);
        return (
          <group key={i} position={position}>
            <Sphere args={[0.05, 16, 16]}>
              <meshStandardMaterial 
                color={market.positive ? '#22c55e' : '#ef4444'}
                emissive={market.positive ? '#22c55e' : '#ef4444'}
                emissiveIntensity={0.5}
              />
            </Sphere>
            <Html distanceFactor={8}>
              <div 
                className="market-label"
                onClick={() => onSelectMarket(market)}
              >
                <span className="market-name">{market.name}</span>
                <span className={`market-value ${market.positive ? 'positive' : 'negative'}`}>
                  {market.value}
                </span>
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

function Globe() {
  const [selectedMarket, setSelectedMarket] = useState(null);

  return (
    <div className="globe-page">
      <div className="globe-header">
        <h1 className="page-title">
          <GlobeIcon size={28} />
          Global Markets
        </h1>
        <div className="market-summary">
          <div className="summary-item positive">
            <TrendingUp size={16} />
            <span>6 Markets Up</span>
          </div>
          <div className="summary-item negative">
            <TrendingDown size={16} />
            <span>2 Markets Down</span>
          </div>
        </div>
      </div>

      <div className="globe-content">
        <div className="globe-container glass-card">
          <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color="#7c3aed" />
            <GlobeMesh onSelectMarket={setSelectedMarket} />
            <OrbitControls 
              enableZoom={true}
              enablePan={false}
              minDistance={3}
              maxDistance={8}
              autoRotate
              autoRotateSpeed={0.5}
            />
          </Canvas>
        </div>

        <div className="globe-sidebar">
          {/* Market List */}
          <div className="sidebar-section glass-card">
            <h3>World Markets</h3>
            <div className="market-list">
              {marketData.map((market, i) => (
                <div 
                  key={i} 
                  className={`market-item ${selectedMarket?.name === market.name ? 'selected' : ''}`}
                  onClick={() => setSelectedMarket(market)}
                >
                  <div className="market-info">
                    <span className="market-city">{market.name}</span>
                    <Activity size={14} className={market.positive ? 'positive' : 'negative'} />
                  </div>
                  <span className={`market-change ${market.positive ? 'positive' : 'negative'}`}>
                    {market.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Selected Market Details */}
          {selectedMarket && (
            <div className="sidebar-section glass-card">
              <h3>Market Details</h3>
              <div className="market-details">
                <div className="detail-row">
                  <span className="detail-label">Exchange</span>
                  <span className="detail-value">{selectedMarket.name}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Change</span>
                  <span className={`detail-value ${selectedMarket.positive ? 'positive' : 'negative'}`}>
                    {selectedMarket.value}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Status</span>
                  <span className="detail-value status-open">Open</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Coordinates</span>
                  <span className="detail-value coords">
                    {selectedMarket.lat.toFixed(2)}°, {selectedMarket.lng.toFixed(2)}°
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Globe;
