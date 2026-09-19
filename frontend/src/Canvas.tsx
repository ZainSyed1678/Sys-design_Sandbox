import React, { useState, useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Background,
  Controls,
  Connection,
  Edge,
  EdgeChange,
  Node,
  NodeChange,
} from 'reactflow';
import { io } from 'socket.io-client';
import { InfrastructureNode } from './nodes/InfrastructureNode';

const nodeTypes = {
  infra: InfrastructureNode,
};

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];
let id = 0;
const getId = () => `dndnode_${id++}`;

const TUTORIAL_TEXT = `
Grog's Guide to System Design!
1. Draw Boxes: Click buttons on the left to add boxes.
2. Connect Boxes: Drag lines from bottom dots to top dots.
3. Start Math: Click "Start Fast Magic".
4. Break Things: Click a box on the grid, then click "Kill Box" at the top.
5. Fix Things: Click "Fix Box".
6. Delete Box: Click a box and click "Delete Box".
`;

export default function Canvas() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [simId, setSimId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<{warnings: string[], recommendations: string[]} | null>(null);
  const [showTutorial, setShowTutorial] = useState(false);

  useEffect(() => {
    const socket = io('http://localhost:5000');
    socket.on('METRICS_UPDATE', (data) => {
      if (data.sim_id === simId || !simId) {
        setNodes((nds) => 
          nds.map((n) => {
            const m = data.components[n.id];
            if (m) {
              return { ...n, data: { ...n.data, metrics: m } };
            }
            return n;
          })
        );
        if (data.analysis) setAnalysis(data.analysis);
      }
    });
    return () => { socket.disconnect(); };
  }, [simId]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    []
  );
  
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);
  
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const addNode = (type: string, label: string) => {
    const newNode: Node = {
      id: getId(),
      type: 'infra',
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      data: { label, type },
    };
    setNodes((nds) => nds.concat(newNode));
  };

  const deleteSelectedNode = () => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter(n => n.id !== selectedNodeId));
    setEdges((eds) => eds.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  };

  const startSimulation = async () => {
    const graph = { nodes, edges };
    try {
      const res = await fetch('http://localhost:5000/api/simulation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setSimId(data.sim_id);
        setAnalysis(null);
      } else {
        alert('Grog say: Bad Math! ' + data.message);
      }
    } catch (e) {
      alert('Brain is dead. Cannot start math.');
    }
  };

  const stopSimulation = async () => {
    if (!simId) return;
    await fetch(`http://localhost:5000/api/simulation/${simId}/stop`, { method: 'POST' });
    setSimId(null);
  };

  const injectChaos = async (type: string) => {
    if (!simId || !selectedNodeId) return;
    await fetch(`http://localhost:5000/api/simulation/${simId}/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_id: selectedNodeId, event_type: type })
    });
  };

  const nodeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach(n => {
      const t = n.data.type || 'unknown';
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [nodes]);

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', width: '100%', height: '100%' }}>
      <div className="sidebar-left">
        <button className="sidebar-btn" onClick={() => addNode('client', 'Client')}>+ Client <span className="badge">{nodeCounts['client'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('load_balancer', 'LB')}>+ Load Balancer <span className="badge">{nodeCounts['load_balancer'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('api', 'API Server')}>+ API <span className="badge">{nodeCounts['api'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('database', 'Database')}>+ DB <span className="badge">{nodeCounts['database'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('cache', 'Cache')}>+ Cache <span className="badge">{nodeCounts['cache'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('queue', 'Queue')}>+ Queue <span className="badge">{nodeCounts['queue'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('worker', 'Worker')}>+ Worker <span className="badge">{nodeCounts['worker'] || 0}</span></button>
        
        <div style={{ marginTop: 'auto' }}>
          <button className="sidebar-btn magic-btn" onClick={startSimulation}>Start Fast Magic</button>
          <button className="sidebar-btn stop-btn" onClick={stopSimulation}>Stop</button>
        </div>
      </div>
      
      <div style={{ flex: 1, position: 'relative' }}>
        {selectedNodeId && (
          <div className="floating-toolbar">
            <span>Selected: {selectedNodeId}</span>
            <button onClick={() => injectChaos('COMPONENT_FAILED')} className="danger-btn">Kill Box</button>
            <button onClick={() => injectChaos('COMPONENT_RECOVERED')} className="safe-btn">Fix Box</button>
            <button onClick={deleteSelectedNode} className="danger-btn" style={{ marginLeft: 10 }}>Delete Box</button>
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background color="#555" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
      
      <div className="sidebar-right">
        <h2>Grog Analysis</h2>
        {analysis ? (
          <>
            {analysis.warnings.length > 0 && (
              <div className="analysis-box warnings">
                <h3 style={{ marginTop: 0 }}>Warnings! ⚠</h3>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {analysis.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}
            {analysis.recommendations.length > 0 && (
              <div className="analysis-box recs">
                <h3 style={{ marginTop: 0 }}>Grog Says:</h3>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </>
        ) : (
          <p style={{ color: '#888' }}>Math is good. Grog is sleeping.</p>
        )}
      </div>
    </div>
  );
}
