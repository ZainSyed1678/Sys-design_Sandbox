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

  const saveArchitecture = async () => {
    const graph = { nodes, edges };
    try {
      const res = await fetch('http://localhost:5000/api/architecture/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        alert('Grog say: Good Rock!');
      } else {
        alert('Grog say: Bad Rock! ' + data.message);
      }
    } catch (e) {
      alert('Brain is dead. Cannot save.');
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <div className="toolbar">
        <button onClick={() => addNode('client', 'Client')}>+ Client</button>
        <button onClick={() => addNode('load_balancer', 'LB')}>+ Load Balancer</button>
        <button onClick={() => addNode('api', 'API Server')}>+ API</button>
        <button onClick={() => addNode('database', 'Database')}>+ DB</button>
        <button onClick={() => addNode('cache', 'Cache')}>+ Cache</button>
        <button onClick={saveArchitecture} style={{ background: '#aed581' }}>Save Rock (JSON)</button>
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
