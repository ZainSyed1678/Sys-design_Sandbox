import React, { useState, useCallback, useMemo } from 'react';
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
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { LLDNode, LLDNodeData } from './nodes/LLDNode';
import { LLDSpecificationsPanel } from './components/LLDSpecificationsPanel';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const nodeTypes = {
  lld: LLDNode,
};

let lldId = 0;
const getLLDId = () => `lld_${lldId++}`;

const initialLLDNodes: Node<LLDNodeData>[] = [
  {
    id: 'lld_user_controller',
    type: 'lld',
    position: { x: 50, y: 120 },
    data: {
      label: 'UserController',
      stereotype: 'controller',
      attributes: [
        { id: 'a1', visibility: '-', name: 'userService', type: 'IUserService' },
      ],
      methods: [
        { id: 'm1', visibility: '+', name: 'getUser', params: 'id: string', returnType: 'UserDTO' },
        { id: 'm2', visibility: '+', name: 'createUser', params: 'req: CreateUserReq', returnType: 'UserDTO' },
      ],
    },
  },
  {
    id: 'lld_user_service_interface',
    type: 'lld',
    position: { x: 380, y: 50 },
    data: {
      label: 'IUserService',
      stereotype: 'interface',
      attributes: [],
      methods: [
        { id: 'm3', visibility: '+', name: 'findById', params: 'id: string', returnType: 'User' },
        { id: 'm4', visibility: '+', name: 'save', params: 'user: User', returnType: 'User' },
      ],
    },
  },
  {
    id: 'lld_user_service_impl',
    type: 'lld',
    position: { x: 380, y: 250 },
    data: {
      label: 'UserService',
      stereotype: 'service',
      attributes: [
        { id: 'a2', visibility: '-', name: 'userRepo', type: 'IUserRepository' },
      ],
      methods: [
        { id: 'm5', visibility: '+', name: 'findById', params: 'id: string', returnType: 'User' },
        { id: 'm6', visibility: '+', name: 'save', params: 'user: User', returnType: 'User' },
      ],
    },
  },
];

const initialLLDEdges: Edge[] = [
  {
    id: 'e_ctrl_svc',
    source: 'lld_user_controller',
    target: 'lld_user_service_interface',
    animated: true,
    label: 'uses',
    markerEnd: { type: MarkerType.ArrowClosed },
  },
  {
    id: 'e_impl_interface',
    source: 'lld_user_service_impl',
    target: 'lld_user_service_interface',
    style: { strokeDasharray: '5,5' },
    label: 'implements',
    markerEnd: { type: MarkerType.ArrowClosed },
  },
];

export function LLDCanvas() {
  const [nodes, setNodes] = useState<Node<LLDNodeData>[]>(initialLLDNodes);
  const [edges, setEdges] = useState<Edge[]>(initialLLDEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [validationModal, setValidationModal] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
    class_count: number;
    relationship_count: number;
  } | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds) as Node<LLDNodeData>[]),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            label: 'depends on',
            markerEnd: { type: MarkerType.ArrowClosed },
          },
          eds
        )
      );
    },
    []
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const addLLDNode = (stereotype: LLDNodeData['stereotype'], label: string) => {
    const newNode: Node<LLDNodeData> = {
      id: getLLDId(),
      type: 'lld',
      position: { x: Math.random() * 150 + 150, y: Math.random() * 150 + 150 },
      data: {
        label,
        stereotype,
        patternType: stereotype === 'pattern' ? 'Strategy' : undefined,
        attributes: [
          { id: `a_${Date.now()}`, visibility: '-', name: 'id', type: 'string' }
        ],
        methods: [
          { id: `m_${Date.now()}`, visibility: '+', name: 'execute', params: '', returnType: 'void' }
        ],
      },
    };
    setNodes((nds) => nds.concat(newNode));
    setSelectedNodeId(newNode.id);
  };

  const deleteSelectedNode = () => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setEdges((eds) => eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  };

  const validateArchitecture = async () => {
    setIsValidating(true);
    try {
      const res = await fetch(`${API_URL}/api/lld/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges }),
      });
      const data = await res.json();
      setValidationModal(data);
    } catch (e: any) {
      alert('Validation Error: Unable to reach backend validation service');
    } finally {
      setIsValidating(false);
    }
  };

  const exportZipArchive = async () => {
    setIsExporting(true);
    try {
      const res = await fetch(`${API_URL}/api/lld/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges }),
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'lld_architecture_skeletons.zip';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert('Export Error: Unable to generate ZIP archive');
    } finally {
      setIsExporting(false);
    }
  };

  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  const handleUpdateNode = (updated: Node<LLDNodeData>) => {
    setNodes((nds) => nds.map((n) => (n.id === updated.id ? updated : n)));
  };

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    nodes.forEach((n) => {
      const s = n.data.stereotype || 'class';
      c[s] = (c[s] || 0) + 1;
    });
    return c;
  }, [nodes]);

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
      {/* Left Sidebar for LLD palette */}
      <div className="sidebar-left">
        <div style={{ fontSize: '0.85rem', color: '#90caf9', fontWeight: 600, marginBottom: 5 }}>
          Object-Oriented Blocks
        </div>
        <button className="sidebar-btn" onClick={() => addLLDNode('class', 'NewClass')}>
          + Class <span className="badge">{counts['class'] || 0}</span>
        </button>
        <button className="sidebar-btn" onClick={() => addLLDNode('interface', 'INewInterface')}>
          + Interface <span className="badge">{counts['interface'] || 0}</span>
        </button>
        <button className="sidebar-btn" onClick={() => addLLDNode('service', 'OrderService')}>
          + Service <span className="badge">{counts['service'] || 0}</span>
        </button>
        <button className="sidebar-btn" onClick={() => addLLDNode('repository', 'OrderRepository')}>
          + Repository <span className="badge">{counts['repository'] || 0}</span>
        </button>
        <button className="sidebar-btn" onClick={() => addLLDNode('controller', 'OrderController')}>
          + Controller <span className="badge">{counts['controller'] || 0}</span>
        </button>
        <button className="sidebar-btn" onClick={() => addLLDNode('pattern', 'PaymentStrategy')}>
          + Design Pattern <span className="badge">{counts['pattern'] || 0}</span>
        </button>

        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button
            className="sidebar-btn primary-btn"
            onClick={validateArchitecture}
            disabled={isValidating}
          >
            {isValidating ? 'Validating...' : '✓ Validate UML'}
          </button>
          <button
            className="sidebar-btn"
            style={{ background: '#1976d2', color: '#fff' }}
            onClick={exportZipArchive}
            disabled={isExporting}
          >
            {isExporting ? 'Packaging...' : '📦 Export ZIP'}
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div style={{ flex: 1, position: 'relative' }}>
        {selectedNodeId && (
          <div className="floating-toolbar">
            <span>Selected: <strong>{selectedNode?.data.label}</strong></span>
            <button onClick={deleteSelectedNode} className="danger-btn">Delete Node</button>
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
          <Background color="#444" gap={18} />
          <Controls />
        </ReactFlow>
      </div>

      {/* Right Drawer: Specifications Panel */}
      {selectedNode && (
        <LLDSpecificationsPanel
          node={selectedNode}
          onUpdate={handleUpdateNode}
          onClose={() => setSelectedNodeId(null)}
        />
      )}

      {/* Validation Results Modal */}
      {validationModal && (
        <div className="modal-overlay" onClick={() => setValidationModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, color: validationModal.valid ? '#81c784' : '#ef5350' }}>
                {validationModal.valid ? '✓ Architecture Validated' : '⚠ Validation Issues Found'}
              </h2>
              <button onClick={() => setValidationModal(null)} className="spec-close-btn">&times;</button>
            </div>
            <p style={{ color: '#aaa', fontSize: '0.85rem' }}>
              Verified {validationModal.class_count} classes/interfaces and {validationModal.relationship_count} relationships.
            </p>

            {validationModal.errors.length > 0 && (
              <div style={{ background: 'rgba(239, 83, 80, 0.15)', border: '1px solid #ef5350', padding: 12, borderRadius: 6, marginBottom: 10 }}>
                <strong style={{ color: '#ef5350' }}>Structural Errors:</strong>
                <ul style={{ margin: '6px 0 0', paddingLeft: 20, color: '#ffcdd2' }}>
                  {validationModal.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationModal.warnings.length > 0 && (
              <div style={{ background: 'rgba(255, 167, 38, 0.15)', border: '1px solid #ffa726', padding: 12, borderRadius: 6, marginBottom: 10 }}>
                <strong style={{ color: '#ffa726' }}>Semantic Warnings:</strong>
                <ul style={{ margin: '6px 0 0', paddingLeft: 20, color: '#ffe0b2' }}>
                  {validationModal.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationModal.valid && validationModal.warnings.length === 0 && (
              <div style={{ color: '#81c784', padding: '10px 0' }}>
                No circular inheritance, illegal extensions, or missing references detected. Code generation will produce valid skeletons.
              </div>
            )}

            <button className="safe-btn" onClick={() => setValidationModal(null)} style={{ marginTop: 10, width: '100%' }}>
              Close Validation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
