import React, { useState } from 'react';
import Canvas from './Canvas';
import { LLDCanvas } from './LLDCanvas';

const TUTORIAL_TEXT = `
System Design Simulator — User Guide

1. High-Level System Design (HLD) Mode:
   - Add Nodes: Select components from the left sidebar (Client, Load Balancer, API Server, Database, Cache, Message Queue, Worker).
   - Connect Services: Drag connectors between component handles to establish traffic routing.
   - Run Simulation: Click "Start Simulation" to initiate discrete-event request flow.
   - Inject Failures: Select a node and click "Fail Node" to test cascading degradation and backpressure.
   - Analysis: Monitor the Architecture Analysis panel on the right for real-time bottleneck detection.

2. Low-Level System Design (LLD) Mode:
   - Click "Low Level System Design" in the top-right mode switcher.
   - Model object-oriented architectures using Classes, Interfaces, Services, Repositories, and Design Patterns.
   - Open the Specifications Drawer on any selected component to define attributes and methods.
   - Inspect and export automatically generated TypeScript and Python code skeletons.
`;

function App() {
  const [mode, setMode] = useState<'hld' | 'lld'>('hld');
  const [showTutorial, setShowTutorial] = useState(false);

  return (
    <div className="dark-theme" style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Universal Topbar */}
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h2>System Design Simulator</h2>
          <button onClick={() => setShowTutorial(true)} className="btn-tutorial">
            Simulator Guide
          </button>
        </div>

        {/* Top Right Mode Toggle Buttons */}
        <div className="mode-toggle-group">
          <button 
            className={`mode-btn ${mode === 'hld' ? 'active' : ''}`}
            onClick={() => setMode('hld')}
          >
            🌐 High Level System Design
          </button>
          <button 
            className={`mode-btn ${mode === 'lld' ? 'active' : ''}`}
            onClick={() => setMode('lld')}
          >
            🧩 Low Level System Design
          </button>
        </div>
      </header>

      {/* Main Workspace Area (Keeps states alive when toggling) */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden', width: '100%', height: '100%' }}>
        <div style={{ flex: 1, display: mode === 'hld' ? 'flex' : 'none', width: '100%', height: '100%' }}>
          <Canvas />
        </div>
        <div style={{ flex: 1, display: mode === 'lld' ? 'flex' : 'none', width: '100%', height: '100%' }}>
          <LLDCanvas />
        </div>
      </main>

      {/* Guide Modal */}
      {showTutorial && (
        <div className="modal-overlay" onClick={() => setShowTutorial(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>System Design Simulator Guide</h2>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{TUTORIAL_TEXT}</pre>
            <button className="safe-btn" onClick={() => setShowTutorial(false)}>
              Close Guide
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
