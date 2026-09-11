import React, { useState, useCallback } from 'react';
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
import { InfrastructureNode } from './nodes/InfrastructureNode';

const nodeTypes = {
  infra: InfrastructureNode,
};

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];
let id = 0;
const getId = () => `dndnode_${id++}`;

export default function Canvas() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [simId, setSimId] = useState<string | null>(null);

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

  const addNode = (type: string, label: string) => {
    const newNode: Node = {
      id: getId(),
      type: 'infra',
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      data: { label, type },
    };
    setNodes((nds) => nds.concat(newNode));
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

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <div className="toolbar">
        <button onClick={() => addNode('client', 'Client')}>+ Client</button>
        <button onClick={() => addNode('load_balancer', 'LB')}>+ Load Balancer</button>
        <button onClick={() => addNode('api', 'API Server')}>+ API</button>
        <button onClick={() => addNode('database', 'Database')}>+ DB</button>
        <button onClick={() => addNode('cache', 'Cache')}>+ Cache</button>
        <button onClick={startSimulation} style={{ background: '#aed581' }}>Start Simulation</button>
        <button onClick={stopSimulation} style={{ background: '#e57373' }}>Stop</button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
