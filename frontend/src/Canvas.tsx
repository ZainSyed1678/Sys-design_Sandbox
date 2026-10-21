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

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const nodeTypes = {
  infra: InfrastructureNode,
};

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];
let id = 0;
const getId = () => `node_${id++}`;

export default function Canvas() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [simId, setSimId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<{warnings: string[], recommendations: string[]} | null>(null);

  useEffect(() => {
    const socket = io(API_URL);
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
      const res = await fetch(`${API_URL}/api/simulation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setSimId(data.sim_id);
        setAnalysis(null);
      } else {
        alert('Simulation Error: ' + data.message);
      }
    } catch (e) {
      alert('Backend connection error: unable to reach the simulation server at ' + API_URL);
    }
  };

  const stopSimulation = async () => {
    if (!simId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/stop`, { method: 'POST' });
    setSimId(null);
  };

  const injectChaos = async (type: string) => {
    if (!simId || !selectedNodeId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/inject`, {
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
        <button className="sidebar-btn" onClick={() => addNode('load_balancer', 'Load Balancer')}>+ Load Balancer <span className="badge">{nodeCounts['load_balancer'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('api', 'API Server')}>+ API Server <span className="badge">{nodeCounts['api'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('database', 'Database')}>+ Database <span className="badge">{nodeCounts['database'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('cache', 'Cache')}>+ Cache <span className="badge">{nodeCounts['cache'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('queue', 'Queue')}>+ Queue <span className="badge">{nodeCounts['queue'] || 0}</span></button>
        <button className="sidebar-btn" onClick={() => addNode('worker', 'Worker')}>+ Worker <span className="badge">{nodeCounts['worker'] || 0}</span></button>
        
        <div style={{ marginTop: 'auto' }}>
          <button className="sidebar-btn primary-btn magic-btn" onClick={startSimulation}>Start Simulation</button>
          <button className="sidebar-btn stop-btn" onClick={stopSimulation}>Stop</button>
        </div>
      </div>
      
      <div style={{ flex: 1, position: 'relative' }}>
        {selectedNodeId && (
          <div className="floating-toolbar">
            <span>Selected: {selectedNodeId}</span>
            <button onClick={() => injectChaos('COMPONENT_FAILED')} className="danger-btn">Fail Node</button>
            <button onClick={() => injectChaos('COMPONENT_RECOVERED')} className="safe-btn">Recover Node</button>
            <button onClick={deleteSelectedNode} className="danger-btn" style={{ marginLeft: 10 }}>Delete Node</button>
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
        <h2>Architecture Analysis</h2>
        {analysis ? (
          <>
            {analysis.warnings.length > 0 && (
              <div className="analysis-box warnings">
                <h3 style={{ marginTop: 0 }}>System Warnings ⚠</h3>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {analysis.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}
            {analysis.recommendations.length > 0 && (
              <div className="analysis-box recs">
                <h3 style={{ marginTop: 0 }}>System Recommendations:</h3>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </>
        ) : (
          <p style={{ color: '#888' }}>System is stable. No active bottlenecks detected.</p>
        )}
      </div>
    </div>
  );
}
