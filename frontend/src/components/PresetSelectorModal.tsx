import React, { useEffect, useState } from 'react';

interface PresetItem {
  id: string;
  name: string;
  description: string;
  traffic_pattern: string;
  what_to_observe: string;
  graph: any;
}

interface PresetSelectorModalProps {
  apiUrl: string;
  onSelectPreset: (presetGraph: any) => void;
  onClose: () => void;
}

export function PresetSelectorModal({ apiUrl, onSelectPreset, onClose }: PresetSelectorModalProps) {
  const [presets, setPresets] = useState<PresetItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/simulation/presets`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setPresets(data.presets || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch presets');
        setLoading(false);
      });
  }, [apiUrl]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content preset-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, color: '#42a5f5' }}>Architectural Scenario Presets</h2>
          <button onClick={onClose} className="spec-close-btn">&times;</button>
        </div>
        <p style={{ color: '#aaa', fontSize: '0.85rem' }}>
          Select a verified scenario preset to load a pre-configured architecture, traffic workload,
          and observable bottleneck dynamics.
        </p>

        {loading && <div style={{ padding: 20, textAlign: 'center' }}>Loading presets...</div>}
        {error && <div style={{ color: '#ef5350', padding: 10 }}>Error: {error}</div>}

        <div className="preset-grid">
          {presets.map((p) => (
            <div
              key={p.id}
              className="preset-card"
              onClick={() => {
                onSelectPreset(p.graph);
                onClose();
              }}
            >
              <div className="preset-card-title">{p.name}</div>
              <div className="preset-card-desc">{p.description}</div>
              <div className="preset-card-observe">
                <strong>Observe:</strong> {p.what_to_observe}
              </div>
              <div className="preset-card-footer">
                <span>Pattern: <em>{p.traffic_pattern}</em></span>
                <button className="preset-load-btn">Load Architecture &rarr;</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
