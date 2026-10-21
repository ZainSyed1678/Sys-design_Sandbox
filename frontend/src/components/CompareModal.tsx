import React, { useState } from 'react';

interface CompareModalProps {
  apiUrl: string;
  currentGraph: any;
  onClose: () => void;
}

export function CompareModal({ apiUrl, currentGraph, onClose }: CompareModalProps) {
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(10.0);
  const [cacheScaling, setCacheScaling] = useState(true);

  const runComparison = async () => {
    setComparing(true);
    setError(null);

    // Architecture A: Current Canvas Graph
    const archA = {
      name: 'Architecture A (Current Canvas)',
      nodes: currentGraph.nodes || [],
      edges: currentGraph.edges || [],
    };

    // Architecture B: Optimized Variant (e.g. adding cache layer or doubling concurrency)
    const modifiedNodes = (currentGraph.nodes || []).map((n: any) => {
      if (cacheScaling && n.data?.type === 'api') {
        return {
          ...n,
          data: {
            ...n.data,
            concurrency: (Number(n.data?.concurrency || 10) * 2),
            circuit_breaker: true,
          },
        };
      }
      return n;
    });

    const archB = {
      name: 'Architecture B (Scaled Workers + Circuit Breakers)',
      nodes: modifiedNodes,
      edges: currentGraph.edges || [],
    };

    try {
      const res = await fetch(`${apiUrl}/api/simulation/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          architecture_a: archA,
          architecture_b: archB,
          duration: Number(duration),
          seed: 42,
        }),
      });

      const data = await res.json();
      if (!res.ok || data.status !== 'ok') {
        throw new Error(data.message || 'Comparison failed');
      }
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Failed to execute comparative simulation');
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content compare-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, color: '#42a5f5' }}>Architecture Compare Mode</h2>
          <button onClick={onClose} className="spec-close-btn">&times;</button>
        </div>
        <p style={{ color: '#aaa', fontSize: '0.85rem' }}>
          Execute dual architectures under identical random seeds and traffic workloads to measure
          exact latency, throughput, drop rate, and cloud cost trade-offs.
        </p>

        {!result && (
          <div style={{ background: '#25252f', padding: 15, borderRadius: 8, margin: '15px 0' }}>
            <div className="form-group">
              <label>Simulated Duration (seconds)</label>
              <input
                type="number"
                min="1"
                max="60"
                className="prop-input"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </div>
            <div className="prop-checkbox-row">
              <input
                type="checkbox"
                id="cache-scaling"
                checked={cacheScaling}
                onChange={(e) => setCacheScaling(e.target.checked)}
              />
              <label htmlFor="cache-scaling">
                Compare Against: Scaled Workers (2x) + Circuit Breakers
              </label>
            </div>
            <button
              onClick={runComparison}
              disabled={comparing}
              className="safe-btn"
              style={{ width: '100%', marginTop: 10, padding: '10px' }}
            >
              {comparing ? 'Simulating Both Architectures...' : 'Run Comparative Benchmark'}
            </button>
            {error && <div style={{ color: '#ef5350', marginTop: 10 }}>{error}</div>}
          </div>
        )}

        {result && (
          <div className="compare-results">
            {/* Verdict Box */}
            <div className="compare-verdict-box">
              <div style={{ fontSize: '0.85rem', color: '#90caf9', fontWeight: 600 }}>
                SYNTHESIZED COMPARISON VERDICT
              </div>
              <div style={{ fontSize: '1rem', marginTop: 4, color: '#fff' }}>
                {result.comparison?.verdict}
              </div>
            </div>

            {/* Side by side cards */}
            <div className="compare-grid">
              <div className="compare-card">
                <h4>{result.architecture_a?.name}</h4>
                <div className="metric-row">
                  <span>Throughput:</span>
                  <strong>{result.architecture_a?.metrics?.throughput?.toFixed(1)} req/s</strong>
                </div>
                <div className="metric-row">
                  <span>p95 Latency:</span>
                  <strong>{(result.architecture_a?.metrics?.latency_p95 * 1000).toFixed(0)} ms</strong>
                </div>
                <div className="metric-row">
                  <span>Drop Rate:</span>
                  <strong>{(result.architecture_a?.metrics?.drop_rate * 100).toFixed(1)}%</strong>
                </div>
                <div className="metric-row">
                  <span>Estimated Cost:</span>
                  <strong>${result.architecture_a?.cost?.total_hourly_cost?.toFixed(2)}/hr</strong>
                </div>
              </div>

              <div className="compare-card highlight">
                <h4>{result.architecture_b?.name}</h4>
                <div className="metric-row">
                  <span>Throughput:</span>
                  <strong>{result.architecture_b?.metrics?.throughput?.toFixed(1)} req/s</strong>
                </div>
                <div className="metric-row">
                  <span>p95 Latency:</span>
                  <strong>{(result.architecture_b?.metrics?.latency_p95 * 1000).toFixed(0)} ms</strong>
                </div>
                <div className="metric-row">
                  <span>Drop Rate:</span>
                  <strong>{(result.architecture_b?.metrics?.drop_rate * 100).toFixed(1)}%</strong>
                </div>
                <div className="metric-row">
                  <span>Estimated Cost:</span>
                  <strong>${result.architecture_b?.cost?.total_hourly_cost?.toFixed(2)}/hr</strong>
                </div>
              </div>
            </div>

            <button
              onClick={() => setResult(null)}
              className="sidebar-btn"
              style={{ marginTop: 15, width: '100%', textAlign: 'center' }}
            >
              Run Another Comparison
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
