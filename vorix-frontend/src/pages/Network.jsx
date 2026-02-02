import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Search, RefreshCw, ZoomIn, ZoomOut } from 'lucide-react';
import { networkAPI } from '../api';
import './Network.css';

// Mock network data
const mockData = {
  nodes: [
    { id: 'AAPL', name: 'Apple', sector: 'Technology', value: 100 },
    { id: 'MSFT', name: 'Microsoft', sector: 'Technology', value: 95 },
    { id: 'GOOGL', name: 'Google', sector: 'Technology', value: 90 },
    { id: 'AMZN', name: 'Amazon', sector: 'Technology', value: 85 },
    { id: 'NVDA', name: 'NVIDIA', sector: 'Technology', value: 80 },
    { id: 'META', name: 'Meta', sector: 'Technology', value: 75 },
    { id: 'TSLA', name: 'Tesla', sector: 'Automotive', value: 70 },
    { id: 'JPM', name: 'JPMorgan', sector: 'Finance', value: 65 },
    { id: 'V', name: 'Visa', sector: 'Finance', value: 60 },
    { id: 'JNJ', name: 'Johnson & Johnson', sector: 'Healthcare', value: 55 },
    { id: 'UNH', name: 'UnitedHealth', sector: 'Healthcare', value: 50 },
    { id: 'XOM', name: 'ExxonMobil', sector: 'Energy', value: 45 },
  ],
  links: [
    { source: 'AAPL', target: 'MSFT', strength: 0.9 },
    { source: 'AAPL', target: 'GOOGL', strength: 0.8 },
    { source: 'MSFT', target: 'GOOGL', strength: 0.85 },
    { source: 'GOOGL', target: 'META', strength: 0.75 },
    { source: 'AMZN', target: 'MSFT', strength: 0.7 },
    { source: 'NVDA', target: 'AAPL', strength: 0.65 },
    { source: 'NVDA', target: 'MSFT', strength: 0.6 },
    { source: 'NVDA', target: 'META', strength: 0.55 },
    { source: 'TSLA', target: 'NVDA', strength: 0.5 },
    { source: 'JPM', target: 'V', strength: 0.8 },
    { source: 'JNJ', target: 'UNH', strength: 0.7 },
    { source: 'AAPL', target: 'AMZN', strength: 0.6 },
    { source: 'META', target: 'AMZN', strength: 0.5 },
  ]
};

const sectorColors = {
  Technology: '#7c3aed',
  Finance: '#22c55e',
  Healthcare: '#3b82f6',
  Energy: '#f59e0b',
  Automotive: '#ef4444'
};

function Network() {
  const svgRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    const container = svg.append('g');

    // Create simulation
    const simulation = d3.forceSimulation(mockData.nodes)
      .force('link', d3.forceLink(mockData.links).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    // Draw links
    const links = container.append('g')
      .selectAll('line')
      .data(mockData.links)
      .join('line')
      .attr('stroke', 'rgba(124, 58, 237, 0.3)')
      .attr('stroke-width', d => d.strength * 3);

    // Draw node groups
    const nodes = container.append('g')
      .selectAll('g')
      .data(mockData.nodes)
      .join('g')
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
        }));

    // Node circles
    nodes.append('circle')
      .attr('r', d => 20 + d.value / 10)
      .attr('fill', d => sectorColors[d.sector] || '#7c3aed')
      .attr('fill-opacity', 0.8)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('mouseover', function() {
        d3.select(this).attr('stroke-width', 3).attr('fill-opacity', 1);
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-width', 2).attr('fill-opacity', 0.8);
      })
      .on('click', (event, d) => {
        setSelectedNode(d);
      });

    // Node labels
    nodes.append('text')
      .text(d => d.id)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#fff')
      .attr('font-size', '11px')
      .attr('font-weight', '600')
      .style('pointer-events', 'none');

    // Update positions on tick
    simulation.on('tick', () => {
      links
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      nodes.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, []);

  return (
    <div className="network-page">
      <div className="network-header">
        <h1 className="page-title">Stock Network</h1>
        <div className="network-controls">
          <div className="network-search">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search stock..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="control-btn">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      <div className="network-content">
        <div className="network-graph glass-card">
          <svg ref={svgRef}></svg>
        </div>

        <div className="network-sidebar">
          {/* Legend */}
          <div className="sidebar-section glass-card">
            <h3>Sectors</h3>
            <div className="legend-list">
              {Object.entries(sectorColors).map(([sector, color]) => (
                <div key={sector} className="legend-item">
                  <span className="legend-dot" style={{ background: color }}></span>
                  <span>{sector}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Selected Node Info */}
          {selectedNode && (
            <div className="sidebar-section glass-card">
              <h3>Selected Stock</h3>
              <div className="node-info">
                <div className="info-row">
                  <span className="info-label">Symbol</span>
                  <span className="info-value">{selectedNode.id}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Name</span>
                  <span className="info-value">{selectedNode.name}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Sector</span>
                  <span 
                    className="info-value sector-tag" 
                    style={{ background: sectorColors[selectedNode.sector] }}
                  >
                    {selectedNode.sector}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="sidebar-section glass-card">
            <h3>Network Stats</h3>
            <div className="stats-list">
              <div className="stat-row">
                <span>Total Nodes</span>
                <span>{mockData.nodes.length}</span>
              </div>
              <div className="stat-row">
                <span>Total Connections</span>
                <span>{mockData.links.length}</span>
              </div>
              <div className="stat-row">
                <span>Avg. Connections</span>
                <span>{(mockData.links.length * 2 / mockData.nodes.length).toFixed(1)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Network;
