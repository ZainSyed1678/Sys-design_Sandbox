import React, { useState } from 'react';
import Canvas from './Canvas';
import { LLDCanvas } from './LLDCanvas';

const TUTORIAL_TEXT = `
Grog's Guide to System Design!

1. High Level System Design (HLD):
   - Click "+ Client", "+ API", "+ Database" to draw infrastructure.
   - Drag lines to connect boxes.
   - Click "Start Fast Magic" to run real-time traffic and queue simulation.
   - Click any box and click "Kill Box" to simulate server or database outages and watch cascading failures.

2. Low Level System Design (LLD):
   - Click "Low Level System Design" button on the top right.
   - Add Class, Interface, Service, Repository, Controller, or Design Pattern.
   - Click any box to open the Specifications Drawer.
   - Add attributes, methods, parameters, and view generated TypeScript / Python code skeletons!
`;

function App() {
  const [mode, setMode] = useState<'hld' | 'lld'>('hld');
  const [showTutorial, setShowTutorial] = useState(false);

  return (
    <div className="dark-theme" style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Universal Topbar */}
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h2>Grog System Simulator</h2>
          <button onClick={() => setShowTutorial(true)} className="btn-tutorial">
            How to use Cave
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

      {/* Beginner Tutorial Modal */}
      {showTutorial && (
        <div className="modal-overlay" onClick={() => setShowTutorial(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Grog's Tutorial</h2>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{TUTORIAL_TEXT}</pre>
            <button className="safe-btn" onClick={() => setShowTutorial(false)}>
              Ugh! I understand
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
