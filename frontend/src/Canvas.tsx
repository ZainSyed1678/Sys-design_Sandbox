import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
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
import 'reactflow/dist/style.css';
import { io, Socket } from 'socket.io-client';
import { InfrastructureNode } from './nodes/InfrastructureNode';
import { TelemetryCharts } from './components/TelemetryCharts';
import { PropertiesPanel } from './components/PropertiesPanel';
import { PresetSelectorModal } from './components/PresetSelectorModal';
import { CompareModal } from './components/CompareModal';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const nodeTypes = {
  infra: InfrastructureNode,
};

let nodeIdCounter = 0;
const getNextNodeId = () => `node_${nodeIdCounter++}`;

const initialNodes: Node[] = [
  {
    id: 'client_1',
    type: 'infra',
    position: { x: 50, y: 150 },
    data: {
      label: 'Client Traffic',
      type: 'client',
      rate_per_sec: 25,
      arrival_process: 'poisson',
    },
  },
  {
    id: 'lb_1',
    type: 'infra',
    position: { x: 280, y: 150 },
    data: {
      label: 'Load Balancer',
      type: 'load_balancer',
      strategy: 'round_robin',
    },
  },
  {
    id: 'api_1',
    type: 'infra',
    position: { x: 520, y: 80 },
    data: {
      label: 'API Server 1',
      type: 'api',
      concurrency: 10,
      latency: 0.05,
      distribution: 'exponential',
      max_queue_depth: 30,
    },
  },
  {
    id: 'api_2',
    type: 'infra',
    position: { x: 520, y: 220 },
    data: {
      label: 'API Server 2',
      type: 'api',
      concurrency: 10,
      latency: 0.05,
      distribution: 'exponential',
      max_queue_depth: 30,
    },
  },
  {
    id: 'db_1',
    type: 'infra',
    position: { x: 760, y: 150 },
    data: {
      label: 'Primary Database',
      type: 'database',
      concurrency: 5,
      latency: 0.1,
      distribution: 'exponential',
      max_queue_depth: 50,
    },
  },
];

const initialEdges: Edge[] = [
  { id: 'e_c_lb', source: 'client_1', target: 'lb_1', animated: true },
  { id: 'e_lb_api1', source: 'lb_1', target: 'api_1', animated: true },
  { id: 'e_lb_api2', source: 'lb_1', target: 'api_2', animated: true },
  { id: 'e_api1_db', source: 'api_1', target: 'db_1', animated: true },
  { id: 'e_api2_db', source: 'api_2', target: 'db_1', animated: true },
];

export default function Canvas() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [simId, setSimId] = useState<string | null>(null);
  const [simState, setSimState] = useState<'IDLE' | 'RUNNING' | 'PAUSED' | 'STOPPED'>('IDLE');
  const [simSpeed, setSimSpeed] = useState<number>(1.0);
  const [isConnected, setIsConnected] = useState<boolean>(true);

  // Selection state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Right sidebar active tab
  const [activeTab, setActiveTab] = useState<'telemetry' | 'properties' | 'analysis'>('telemetry');

  // Modals
  const [showPresets, setShowPresets] = useState<boolean>(false);
  const [showCompare, setShowCompare] = useState<boolean>(false);

  // Live telemetry & analysis
  const [systemMetrics, setSystemMetrics] = useState<any>({});
  const [systemHistory, setSystemHistory] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);

  const socketRef = useRef<Socket | null>(null);

  // Setup SocketIO with session room joining
  useEffect(() => {
    const socket = io(API_URL, {
      reconnectionAttempts: 20,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      if (simId) {
        socket.emit('join_simulation', { sim_id: simId });
      }
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    socket.on('connect_error', () => {
      setIsConnected(false);
    });

    socket.on('METRICS_UPDATE', (data) => {
      if (!simId || data.sim_id === simId) {
        if (data.metrics) setSystemMetrics(data.metrics);
        if (data.system_history) setSystemHistory(data.system_history);
        if (data.analysis) setAnalysis(data.analysis);
        if (data.state) {
          const s = String(data.state).toUpperCase();
          if (s === 'RUNNING') setSimState('RUNNING');
          else if (s === 'PAUSED') setSimState('PAUSED');
          else if (s === 'STOPPED') setSimState('STOPPED');
        }

        // Update component metrics inside node.data
        if (data.components) {
          setNodes((nds) =>
            nds.map((n) => {
              const compState = data.components[n.id];
              if (compState) {
                return {
                  ...n,
                  data: {
                    ...n.data,
                    metrics: compState,
                  },
                };
              }
              return n;
            })
          );
        }
      }
    });

    socket.on('SIM_PAUSED', (data) => {
      if (data.sim_id === simId) setSimState('PAUSED');
    });

    socket.on('SIM_RESUMED', (data) => {
      if (data.sim_id === simId) setSimState('RUNNING');
    });

    socket.on('SIM_STOPPED', (data) => {
      if (data.sim_id === simId) setSimState('STOPPED');
    });

    return () => {
      socket.disconnect();
    };
  }, [simId]);

  // Keyboard accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput =
        activeEl &&
        (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT');
      if (isInput) return;

      if (e.code === 'Space') {
        e.preventDefault();
        if (simState === 'RUNNING') pauseSimulation();
        else if (simState === 'PAUSED') resumeSimulation();
        else startSimulation();
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        stepSimulation();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        resetSimulation();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodeId) {
          e.preventDefault();
          deleteSelectedNode();
        } else if (selectedEdgeId) {
          e.preventDefault();
          deleteSelectedEdge();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [simState, simId, selectedNodeId, selectedEdgeId, nodes, edges]);

  // Node & edge change handlers
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) => addEdge({ ...connection, animated: true }, eds)),
    []
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    setSelectedEdgeId(null);
  }, []);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id);
    setSelectedNodeId(null);
    setActiveTab('properties');
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  }, []);

  const addNode = (type: string, label: string) => {
    const newNode: Node = {
      id: getNextNodeId(),
      type: 'infra',
      position: { x: Math.random() * 250 + 100, y: Math.random() * 250 + 100 },
      data: {
        label,
        type,
        concurrency: 10,
        latency: 0.05,
        distribution: 'constant',
        max_queue_depth: 50,
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

  const deleteSelectedEdge = () => {
    if (!selectedEdgeId) return;
    setEdges((eds) => eds.filter((e) => e.id !== selectedEdgeId));
    setSelectedEdgeId(null);
  };

  // Simulation Controls
  const startSimulation = async () => {
    const graph = { nodes, edges, seed: 42 };
    try {
      const res = await fetch(`${API_URL}/api/simulation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setSimId(data.sim_id);
        setSimState('RUNNING');
        if (socketRef.current) {
          socketRef.current.emit('join_simulation', { sim_id: data.sim_id });
        }
      } else {
        alert('Simulation Error: ' + data.message);
      }
    } catch (e) {
      alert('Backend connection error: unable to reach the simulation server at ' + API_URL);
    }
  };

  const pauseSimulation = async () => {
    if (!simId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/pause`, { method: 'POST' });
    setSimState('PAUSED');
  };

  const resumeSimulation = async () => {
    if (!simId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/resume`, { method: 'POST' });
    setSimState('RUNNING');
  };

  const stepSimulation = async () => {
    if (!simId) {
      await startSimulation();
      return;
    }
    await fetch(`${API_URL}/api/simulation/${simId}/step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seconds: 0.5 }),
    });
    setSimState('PAUSED');
  };

  const resetSimulation = async () => {
    if (simId) {
      await fetch(`${API_URL}/api/simulation/${simId}/reset`, { method: 'POST' });
    }
    setSimId(null);
    setSimState('IDLE');
    setSystemMetrics({});
    setSystemHistory([]);
    setAnalysis(null);
    setNodes((nds) =>
      nds.map((n) => {
        const { metrics, ...restData } = n.data;
        return { ...n, data: restData };
      })
    );
  };

  const stopSimulation = async () => {
    if (!simId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/stop`, { method: 'POST' });
    setSimState('STOPPED');
  };

  const changeSpeed = async (speed: number) => {
    setSimSpeed(speed);
    if (simId) {
      await fetch(`${API_URL}/api/simulation/${simId}/speed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed }),
      });
    }
  };

  // Chaos injection
  const injectChaos = async (type: string, payload: any = {}) => {
    if (!simId || !selectedNodeId) return;
    await fetch(`${API_URL}/api/simulation/${simId}/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_id: selectedNodeId,
        event_type: type,
        data: payload,
      }),
    });
  };

  // Node counts for sidebar badges
  const nodeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => {
      const t = n.data?.type || 'unknown';
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [nodes]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedEdgeId) || null,
    [edges, selectedEdgeId]
  );

  const handleUpdateNode = (updated: Node) => {
    setNodes((nds) => nds.map((n) => (n.id === updated.id ? updated : n)));
  };

  const handleUpdateEdge = (updated: Edge) => {
    setEdges((eds) => eds.map((e) => (e.id === updated.id ? updated : e)));
  };

  const handleLoadPreset = (presetGraph: any) => {
    if (presetGraph && presetGraph.nodes && presetGraph.edges) {
      resetSimulation();
      setNodes(presetGraph.nodes);
      setEdges(presetGraph.edges);
    }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', width: '100%', height: '100%' }}>
      {/* Connection Lost Banner */}
      {!isConnected && (
        <div className="connection-lost-banner" role="alert">
          <span style={{ marginRight: 8 }}>⚠️</span>
          <strong>Connection Lost:</strong> Disconnected from simulation backend. Attempting automatic reconnection...
        </div>
      )}

      {/* Main Layout Body */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* Left Sidebar: Infrastructure Palette & Actions */}
        <div className="sidebar-left">
          <div style={{ fontSize: '0.82rem', color: '#90caf9', fontWeight: 600, marginBottom: 4 }}>
            Infrastructure Components
          </div>
          <button className="sidebar-btn" onClick={() => addNode('client', 'Client Traffic')}>
            + Client <span className="badge">{nodeCounts['client'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('load_balancer', 'Load Balancer')}>
            + Load Balancer <span className="badge">{nodeCounts['load_balancer'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('api', 'API Server')}>
            + API Server <span className="badge">{nodeCounts['api'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('database', 'Database')}>
            + Database <span className="badge">{nodeCounts['database'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('cache', 'Cache')}>
            + Cache <span className="badge">{nodeCounts['cache'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('queue', 'Message Queue')}>
            + Queue <span className="badge">{nodeCounts['queue'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('worker', 'Worker Node')}>
            + Worker <span className="badge">{nodeCounts['worker'] || 0}</span>
          </button>
          <button className="sidebar-btn" onClick={() => addNode('cdn', 'Edge Cache / CDN')}>
            + CDN / Edge <span className="badge">{nodeCounts['cdn'] || 0}</span>
          </button>

          <hr style={{ border: 'none', borderTop: '1px solid #3a3a48', margin: '8px 0' }} />

          {/* Preset Scenarios & Compare Mode */}
          <button className="sidebar-btn" onClick={() => setShowPresets(true)} style={{ color: '#ce93d8' }}>
            📚 Scenario Presets
          </button>
          <button className="sidebar-btn" onClick={() => setShowCompare(true)} style={{ color: '#80deea' }}>
            ⚖️ Compare Mode
          </button>

          {/* Quick Shortcuts Legend */}
          <div style={{ marginTop: 'auto', background: '#1e1e24', padding: '10px', borderRadius: '6px', fontSize: '0.72rem', color: '#888', border: '1px solid #3a3a48' }}>
            <div style={{ fontWeight: 600, color: '#aaa', marginBottom: 4 }}>⌨️ Shortcuts</div>
            <div><code>Space</code> : Play / Pause</div>
            <div><code>S</code> : Step (+0.5s)</div>
            <div><code>R</code> : Reset State</div>
            <div><code>Del</code> : Delete Selected</div>
          </div>
        </div>

        {/* Central Canvas Area with Floating Control Toolbar */}
        <div style={{ flex: 1, position: 'relative' }}>
          {/* Accessible Simulation Control Toolbar */}
          <div className="sim-toolbar" role="toolbar" aria-label="Simulation Controls">
            {/* Status indicator */}
            <div className={`sim-status-pill ${simState.toLowerCase()}`}>
              <span className="pulse-dot" />
              {simState}
            </div>

            {/* Play/Pause/Resume */}
            {simState === 'RUNNING' ? (
              <button
                className="sim-ctrl-btn pause"
                onClick={pauseSimulation}
                title="Pause Simulation (Space)"
                aria-label="Pause Simulation"
              >
                ⏸ Pause
              </button>
            ) : simState === 'PAUSED' ? (
              <button
                className="sim-ctrl-btn play"
                onClick={resumeSimulation}
                title="Resume Simulation (Space)"
                aria-label="Resume Simulation"
              >
                ▶ Resume
              </button>
            ) : (
              <button
                className="sim-ctrl-btn play"
                onClick={startSimulation}
                title="Start Discrete Event Simulation (Space)"
                aria-label="Start Simulation"
              >
                ▶ Start Simulation
              </button>
            )}

            {/* Step */}
            <button
              className="sim-ctrl-btn"
              onClick={stepSimulation}
              title="Step forward 0.5s virtual time (S)"
              aria-label="Step forward"
            >
              ⏭ Step (0.5s)
            </button>

            {/* Reset */}
            <button
              className="sim-ctrl-btn"
              onClick={resetSimulation}
              title="Reset simulation and rebuild graph (R)"
              aria-label="Reset simulation"
            >
              🔄 Reset
            </button>

            {/* Stop */}
            {simState !== 'IDLE' && (
              <button
                className="sim-ctrl-btn stop"
                onClick={stopSimulation}
                title="Stop Simulation"
                aria-label="Stop simulation"
              >
                ⏹ Stop
              </button>
            )}

            <div style={{ width: 1, height: 20, background: '#4a4a58', margin: '0 4px' }} />

            {/* Speed Control Slider & Presets */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#ddd' }}>
              <span>Speed:</span>
              <input
                type="range"
                min="0.25"
                max="20"
                step="0.25"
                value={simSpeed}
                onChange={(e) => changeSpeed(Number(e.target.value))}
                style={{ width: '80px', cursor: 'pointer' }}
                aria-label="Simulation Speed Slider"
              />
              <span style={{ minWidth: '42px', fontWeight: 600, color: '#64b5f6' }}>
                {simSpeed}x
              </span>

              {/* Speed Preset Buttons */}
              <button className="speed-preset-btn" onClick={() => changeSpeed(1.0)}>1x</button>
              <button className="speed-preset-btn" onClick={() => changeSpeed(5.0)}>5x</button>
              <button className="speed-preset-btn" onClick={() => changeSpeed(20.0)}>20x</button>
            </div>
          </div>

          {/* Floating Chaos Injection Toolbar when a node is selected */}
          {selectedNodeId && (
            <div className="floating-toolbar">
              <span>Target: <strong>{selectedNode?.data?.label || selectedNodeId}</strong></span>
              <button onClick={() => injectChaos('COMPONENT_FAILED')} className="danger-btn" title="Inject Node Outage">
                Fail Node
              </button>
              <button onClick={() => injectChaos('COMPONENT_DEGRADED', { multiplier: 3.0 })} className="warn-btn" title="Multiply Latency by 3x">
                Degrade (3x)
              </button>
              <button onClick={() => injectChaos('COMPONENT_RECOVERED')} className="safe-btn" title="Recover to Healthy">
                Recover Node
              </button>
              <button onClick={deleteSelectedNode} className="danger-btn" style={{ marginLeft: 8 }} title="Remove from Canvas (Del)">
                Delete Node
              </button>
            </div>
          )}

          {/* React Flow Canvas */}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background color="#444" gap={16} />
            <Controls />
          </ReactFlow>

          {/* Empty Canvas Call-to-Action */}
          {nodes.length === 0 && (
            <div className="canvas-empty-state">
              <div style={{ fontSize: '2.5rem', marginBottom: 10 }}>🌐</div>
              <h3>Interactive Canvas is Empty</h3>
              <p style={{ maxWidth: '420px', color: '#aaa', margin: '6px 0 16px' }}>
                Build your distributed system topology by clicking components from the left sidebar,
                or load a pre-configured architecture scenario preset.
              </p>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="safe-btn"
                  onClick={() => {
                    setNodes(initialNodes);
                    setEdges(initialEdges);
                  }}
                >
                  Load Starter Architecture
                </button>
                <button className="sidebar-btn" onClick={() => setShowPresets(true)}>
                  Explore Scenario Presets
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Dynamic Tabs (Telemetry / Properties / Analysis) */}
        <div className="sidebar-right">
          {/* Top Panel Tab Bar */}
          <div className="right-panel-tabs">
            <button
              className={`panel-tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
              onClick={() => setActiveTab('telemetry')}
            >
              📊 Telemetry
            </button>
            <button
              className={`panel-tab-btn ${activeTab === 'properties' ? 'active' : ''}`}
              onClick={() => setActiveTab('properties')}
            >
              ⚙️ Properties {selectedNodeId ? `(1)` : ''}
            </button>
            <button
              className={`panel-tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
              onClick={() => setActiveTab('analysis')}
            >
              🔍 Analysis {analysis?.findings?.length ? `(${analysis.findings.length})` : ''}
            </button>
          </div>

          {/* Tab 1: Live Telemetry Charts */}
          {activeTab === 'telemetry' && (
            <TelemetryCharts
              selectedNodeId={selectedNodeId}
              selectedNodeLabel={selectedNode?.data?.label}
              selectedNodeMetrics={selectedNode?.data?.metrics}
              systemMetrics={systemMetrics}
              systemHistory={systemHistory}
              onClearSelection={() => setSelectedNodeId(null)}
            />
          )}

          {/* Tab 2: Properties & Configurations */}
          {activeTab === 'properties' && (
            <div>
              {selectedNode || selectedEdge ? (
                <PropertiesPanel
                  selectedNode={selectedNode}
                  selectedEdge={selectedEdge}
                  onUpdateNode={handleUpdateNode}
                  onUpdateEdge={handleUpdateEdge}
                  onClose={() => {
                    setSelectedNodeId(null);
                    setSelectedEdgeId(null);
                  }}
                />
              ) : (
                <div style={{ padding: 25, textAlign: 'center', color: '#888' }}>
                  <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>⚙️</div>
                  <div style={{ fontWeight: 600, color: '#bbb', marginBottom: 4 }}>
                    No Component Selected
                  </div>
                  <p style={{ fontSize: '0.8rem' }}>
                    Click any node or connection edge on the canvas to configure concurrency,
                    stochastic service distributions, queue depth, timeouts, retries, and circuit breakers.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Evidence-Based Architecture Analysis */}
          {activeTab === 'analysis' && (
            <div className="analysis-container">
              <h3 style={{ margin: '0 0 10px', fontSize: '1.05rem', color: '#90caf9' }}>
                Architecture Bottleneck Analysis
              </h3>

              {analysis && analysis.findings && analysis.findings.length > 0 ? (
                <div className="findings-list">
                  {analysis.findings.map((f: any, idx: number) => {
                    const sev = f.severity || 'MEDIUM';
                    return (
                      <div key={idx} className={`finding-card ${sev.toLowerCase()}`}>
                        <div className="finding-header">
                          <span className={`finding-sev-badge ${sev.toLowerCase()}`}>
                            {sev}
                          </span>
                          <span className="finding-rule-id">{f.rule_id}</span>
                          {f.node_id && <span className="finding-node">@{f.node_id}</span>}
                        </div>
                        <div className="finding-msg">{f.message}</div>
                        {f.evidence && (
                          <div className="finding-evidence">
                            <strong>Evidence:</strong> {JSON.stringify(f.evidence)}
                          </div>
                        )}
                        {f.recommendation && (
                          <div className="finding-rec">
                            <strong>Recommendation:</strong> {f.recommendation}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="analysis-empty-state">
                  <div style={{ fontSize: '2rem', marginBottom: 8 }}>🛡️</div>
                  <div style={{ fontWeight: 600, color: '#81c784', marginBottom: 4 }}>
                    All Systems Operational
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#aaa', margin: 0 }}>
                    No bottlenecks, queue overflows, retry storms, or single points of failure detected.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Preset Scenarios Modal */}
      {showPresets && (
        <PresetSelectorModal
          apiUrl={API_URL}
          onSelectPreset={handleLoadPreset}
          onClose={() => setShowPresets(false)}
        />
      )}

      {/* Architecture Compare Modal */}
      {showCompare && (
        <CompareModal
          apiUrl={API_URL}
          currentGraph={{ nodes, edges }}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  );
}
