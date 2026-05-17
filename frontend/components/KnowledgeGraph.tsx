'use client';

import React, { useEffect, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import { KGSubgraph } from '@/types/kg';

interface KnowledgeGraphProps {
  data: KGSubgraph;
  onNodeClick: (nodeData: any) => void;
  setCy: (cy: cytoscape.Core) => void;
}

const nodeStyles = [
  {
    selector: 'node',
    style: {
      'label': 'data(label)',
      'color': '#cbd5e1',
      'font-size': '12px',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': '8px',
      'background-color': '#1e293b',
      'border-width': '2px',
      'border-color': '#334155',
      'width': '40px',
      'height': '40px',
      'transition-property': 'background-color, border-color, width, height',
      'transition-duration': '0.3s',
    },
  },
  {
    selector: 'node[type="PERSON"]',
    style: {
      'shape': 'ellipse',
      'background-color': '#3b82f6',
      'border-color': '#2563eb',
    },
  },
  {
    selector: 'node[type="ORG"]',
    style: {
      'shape': 'rectangle',
      'background-color': '#22c55e',
      'border-color': '#16a34a',
    },
  },
  {
    selector: 'node[type="PRODUCT"]',
    style: {
      'shape': 'diamond',
      'background-color': '#eab308',
      'border-color': '#ca8a04',
    },
  },
  {
    selector: 'node[type="CONCEPT"]',
    style: {
      'shape': 'ellipse',
      'background-color': '#a855f7', // Glowing Purple for fields and concepts
      'border-color': '#9333ea',
    },
  },
  {
    selector: 'node[type="EVENT"]',
    style: {
      'shape': 'octagon',
      'background-color': '#f43f5e', // Glowing Rose Pink for timestamps and events
      'border-color': '#e11d48',
    },
  },
  {
    selector: 'node[type="LOCATION"]',
    style: {
      'shape': 'hexagon',
      'background-color': '#06b6d4', // Glowing Cyan for origins and hubs
      'border-color': '#0891b2',
    },
  },
  {
    selector: 'edge',
    style: {
      'label': 'data(label)',
      'font-size': '10px',
      'color': '#94a3b8',
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'target-arrow-color': '#475569',
      'line-color': '#475569',
      'width': '2px',
      'text-rotation': 'autorotate',
      'text-background-opacity': 1,
      'text-background-color': '#020617',
      'text-background-padding': '3px',
      'text-background-shape': 'roundrectangle',
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#6366f1',
      'border-width': '4px',
      'width': '45px',
      'height': '45px',
    },
  },
];

export default function KnowledgeGraph({ data, onNodeClick, setCy }: KnowledgeGraphProps) {
  const cyRef = useRef<cytoscape.Core | null>(null);

  const elements = [
    ...data.nodes.map(n => ({ data: { ...n } })),
    ...data.edges.map(e => ({ data: { ...e } }))
  ];

  useEffect(() => {
    const runLayout = () => {
      if (cyRef.current) {
        // Trigger resize and layout calculation
        cyRef.current.resize();
        const layout = cyRef.current.layout({
          name: 'cose',
          animate: true,
          randomize: true, // Randomize positions first to prevent zero-coordinate overlapping
          fit: true,
          padding: 60,
          nodeOverlap: 40,
          componentSpacing: 120,
          refresh: 20,
          idealEdgeLength: 120,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
        } as any);
        
        layout.run();
        cyRef.current.fit();
      }
    };

    // Run layout with minor timeout to ensure DOM container size matches the CSS flex attributes
    const timer = setTimeout(runLayout, 150);
    return () => clearTimeout(timer);
  }, [data]);

  return (
    <div className="absolute inset-6 bg-[#020617] rounded-3xl overflow-hidden border border-slate-800 shadow-2xl">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={nodeStyles as any}
        cy={(cy) => {
          cyRef.current = cy;
          setCy(cy);
          cy.on('tap', 'node', (evt) => {
            onNodeClick(evt.target.data());
          });
        }}
      />
    </div>
  );
}
