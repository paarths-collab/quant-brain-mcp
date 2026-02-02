import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, ZoomIn, ZoomOut, Maximize2, Filter, RefreshCw, Info } from 'lucide-react';
import * as d3 from 'd3';
import { networkAPI } from '../api';
import './Graph.css';

// Default stock nodes for fallback
const defaultNodes = [
  { id: 'AAPL', name: 'Apple', sector: 'Technology', marketCap: 3200, change: 1.2 },
  { id: 'MSFT', name: 'Microsoft', sector: 'Technology', marketCap: 2900, change: 0.8 },
  { id: 'GOOGL', name: 'Google', sector: 'Technology', marketCap: 1800, change: -0.5 },
  { id: 'NVDA', name: 'NVIDIA', sector: 'Technology', marketCap: 2100, change: 3.5 },
  { id: 'TSLA', name: 'Tesla', sector: 'Technology', marketCap: 800, change: -1.2 },
  { id: 'JPM', name: 'JPMorgan', sector: 'Finance', marketCap: 500, change: 0.6 },
  { id: 'RELIANCE', name: 'Reliance', sector: 'Energy', marketCap: 220, change: 1.8 },
  { id: 'TCS', name: 'TCS', sector: 'Technology', marketCap: 180, change: 0.5 },
  { id: 'HDFCBANK', name: 'HDFC Bank', sector: 'Finance', marketCap: 150, change: 0.9 },
];

const defaultLinks = [
  { source: 'AAPL', target: 'MSFT', strength: 0.8 },
  { source: 'AAPL', target: 'GOOGL', strength: 0.7 },
  { source: 'MSFT', target: 'GOOGL', strength: 0.75 },
  { source: 'NVDA', target: 'AAPL', strength: 0.5 },
  { source: 'NVDA', target: 'MSFT', strength: 0.7 },
  { source: 'TSLA', target: 'NVDA', strength: 0.4 },
  { source: 'TCS', target: 'MSFT', strength: 0.4 },
  { source: 'HDFCBANK', target: 'JPM', strength: 0.3 },
  { source: 'RELIANCE', target: 'TCS', strength: 0.5 },
];

const sectorColors = {
  Technology: '#3b82f6',
  Finance: '#22c55e',
  Healthcare: '#f59e0b',
  Energy: '#ef4444',
  Consumer: '#8b5cf6',
};

function Graph() {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedSector, setSelectedSector] = useState('All');
  const [zoom, setZoom] = useState(1);
  const [stockNodes, setStockNodes] = useState(defaultNodes);
  const [stockLinks, setStockLinks] = useState(defaultLinks);
  const [loading, setLoading] = useState(false);
  const simulationRef = useRef(null);

  // Fetch network data from backend
  const fetchNetworkData = async (symbol = 'AAPL') => {
    setLoading(true);
    try {
      const response = await networkAPI.getGraph(symbol);
      if (response.data) {
        const nodes = response.data.nodes || response.data.stockNodes || defaultNodes;
        const links = response.data.links || response.data.stockLinks || defaultLinks;
        setStockNodes(nodes);
        setStockLinks(links);
      }
    } catch (err) {
      console.error('Network fetch error:', err);
      // Keep default data on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNetworkData();
  }, []);

  const initGraph = useCallback(() => {
    if (!svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // Create zoom behavior
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoom(event.transform.k);
      });

    svg.call(zoomBehavior);

    const g = svg.append('g');

    // Filter nodes by sector
    let filteredNodes = selectedSector === 'All' 
      ? [...stockNodes] 
      : stockNodes.filter(n => n.sector === selectedSector);

    // Filter nodes by search
    if (searchQuery) {
      const query = searchQuery.toUpperCase();
      filteredNodes = filteredNodes.filter(n => 
        n.id.includes(query) || n.name.toUpperCase().includes(query)
      );
    }

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = stockLinks.filter(l => 
      nodeIds.has(l.source) && nodeIds.has(l.target)
    );

    // Create force simulation
    const simulation = d3.forceSimulation(filteredNodes)
      .force('link', d3.forceLink(filteredLinks).id(d => d.id).distance(100).strength(d => d.strength * 0.5))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => Math.sqrt(d.marketCap) * 0.8 + 10));

    simulationRef.current = simulation;

    // Create gradient definitions
    const defs = svg.append('defs');
    
    // Create glow filter
    const filter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    
    filter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'coloredBlur');
    
    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Draw links
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(filteredLinks)
      .enter()
      .append('line')
      .attr('stroke', '#1e3a5f')
      .attr('stroke-opacity', d => d.strength * 0.6)
      .attr('stroke-width', d => d.strength * 3);

    // Draw nodes
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(filteredNodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Node circles
    node.append('circle')
      .attr('r', d => Math.sqrt(d.marketCap) * 0.6 + 8)
      .attr('fill', d => sectorColors[d.sector] || '#3b82f6')
      .attr('stroke', d => d.change >= 0 ? '#22c55e' : '#ef4444')
      .attr('stroke-width', 2)
      .attr('filter', 'url(#glow)')
      .on('click', (event, d) => {
        event.stopPropagation();
        setSelectedNode(d);
      })
      .on('mouseover', function() {
        d3.select(this).attr('stroke-width', 4);
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-width', 2);
      });

    // Node labels
    node.append('text')
      .text(d => d.id)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#fff')
      .attr('font-size', d => Math.min(Math.sqrt(d.marketCap) * 0.3 + 6, 14))
      .attr('font-weight', '600')
      .style('pointer-events', 'none');

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Click on background to deselect
    svg.on('click', () => setSelectedNode(null));

  }, [selectedSector, searchQuery]);

  useEffect(() => {
    initGraph();
    
    const handleResize = () => initGraph();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [initGraph]);

  const handleRefresh = () => {
    if (simulationRef.current) {
      simulationRef.current.alpha(1).restart();
    }
  };

  const sectors = ['All', ...Object.keys(sectorColors)];

  return (
    <div className="graph-page">
      {/* Header */}
      <div className="graph-header">
        <div>
          <h1>📊 Stock Relationship Graph</h1>
          <p>Visualize correlations and connections between stocks</p>
        </div>
        <div className="header-actions">
          <button className="refresh-btn" onClick={handleRefresh}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="graph-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search stock (e.g. AAPL, TCS)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="sector-filters">
          <Filter size={16} />
          {sectors.map(sector => (
            <button
              key={sector}
              className={selectedSector === sector ? 'active' : ''}
              onClick={() => setSelectedSector(sector)}
              style={sector !== 'All' ? { borderColor: sectorColors[sector] } : {}}
            >
              {sector !== 'All' && (
                <span className="sector-dot" style={{ background: sectorColors[sector] }} />
              )}
              {sector}
            </button>
          ))}
        </div>

        <div className="zoom-controls">
          <span>Zoom: {(zoom * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Legend */}
      <div className="graph-legend">
        {Object.entries(sectorColors).map(([sector, color]) => (
          <div key={sector} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            <span>{sector}</span>
          </div>
        ))}
        <div className="legend-item">
          <span className="legend-line positive" />
          <span>Positive</span>
        </div>
        <div className="legend-item">
          <span className="legend-line negative" />
          <span>Negative</span>
        </div>
      </div>

      {/* Graph Container */}
      <div className="graph-container" ref={containerRef}>
        <svg ref={svgRef} />
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="node-info-panel">
          <button className="close-btn" onClick={() => setSelectedNode(null)}>×</button>
          <div className="node-header">
            <span className="node-symbol">{selectedNode.id}</span>
            <span 
              className="node-sector"
              style={{ background: sectorColors[selectedNode.sector] }}
            >
              {selectedNode.sector}
            </span>
          </div>
          <h3>{selectedNode.name}</h3>
          <div className="node-stats">
            <div className="stat">
              <span className="label">Market Cap</span>
              <span className="value">${selectedNode.marketCap}B</span>
            </div>
            <div className="stat">
              <span className="label">Today</span>
              <span className={`value ${selectedNode.change >= 0 ? 'positive' : 'negative'}`}>
                {selectedNode.change >= 0 ? '+' : ''}{selectedNode.change}%
              </span>
            </div>
          </div>
          <div className="connections">
            <h4>Connected Stocks</h4>
            <div className="connection-list">
              {stockLinks
                .filter(l => l.source === selectedNode.id || l.target === selectedNode.id)
                .map((link, i) => {
                  const otherId = link.source === selectedNode.id ? link.target : link.source;
                  const otherNode = stockNodes.find(n => n.id === otherId);
                  return (
                    <div key={i} className="connection-item">
                      <span className="conn-symbol">{otherId}</span>
                      <span className="conn-name">{otherNode?.name}</span>
                      <span className="conn-strength">{(link.strength * 100).toFixed(0)}%</span>
                    </div>
                  );
                })
              }
            </div>
          </div>
        </div>
      )}

      {/* Help Tip */}
      <div className="graph-tip">
        <Info size={14} />
        <span>Drag nodes to rearrange • Click to select • Scroll to zoom</span>
      </div>
    </div>
  );
}

export default Graph;
