'use client';

import React, { useEffect, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { KGSubgraph, EntityType } from '@/types/kg';

// Register layout
if (typeof window !== 'undefined') {
  cytoscape.use(fcose);
}

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
    selector: 'edge',
    style: {
      'label': 'data(label)',
      'font-size': '10px',
      'color': '#64748b',
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'target-arrow-color': '#334155',
      'line-color': '#334155',
      'width': '2px',
      'text-rotation': 'autorotate',
      'text-background-opacity': 1,
      'text-background-color': '#0f172a',
      'text-background-padding': '2px',
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
  const elements = [
    ...data.nodes.map(n => ({ data: { ...n } })),
    ...data.edges.map(e => ({ data: { ...e } }))
  ];

  return (
    <div className="w-full h-full bg-[#020617] rounded-3xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={nodeStyles as any}
        layout={{
          name: 'fcose',
          randomize: false,
          animate: true,
          padding: 50,
          nodeDimensionsIncludeLabels: true,
        } as any}
        cy={(cy) => {
          setCy(cy);
          cy.on('tap', 'node', (evt) => {
            onNodeClick(evt.target.data());
          });
        }}
      />
    </div>
  );
}
