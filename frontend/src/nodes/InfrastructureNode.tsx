import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export interface HealthStateInfo {
  status: 'HEALTHY' | 'DEGRADED' | 'OVERLOADED' | 'FAILED' | 'CIRCUIT_OPEN' | 'CIRCUIT_HALF_OPEN' | 'READY';
  label: string;
  badgeBg: string;
  badgeBorder: string;
  icon: string;
}

export function determineNodeHealth(metrics: any): HealthStateInfo {
  if (!metrics) {
    return {
      status: 'READY',
      label: 'READY',
      badgeBg: '#37474f',
      badgeBorder: '#546e7a',
      icon: '⚪',
    };
  }

  // 1. Hard Component Failure
  if (metrics.healthy === false) {
    return {
      status: 'FAILED',
      label: 'FAILED',
      badgeBg: '#b71c1c',
      badgeBorder: '#ef5350',
      icon: '🔴',
    };
  }

  // 2. Circuit Breaker Open
  if (metrics.circuit_breaker?.state === 'OPEN') {
    return {
      status: 'CIRCUIT_OPEN',
      label: 'CIRCUIT OPEN',
      badgeBg: '#e65100',
      badgeBorder: '#ff9800',
      icon: '⚡',
    };
  }

  // 3. Circuit Breaker Half-Open
  if (metrics.circuit_breaker?.state === 'HALF_OPEN') {
    return {
      status: 'CIRCUIT_HALF_OPEN',
      label: 'HALF OPEN',
      badgeBg: '#f57f17',
      badgeBorder: '#fbc02d',
      icon: '⚠️',
    };
  }

  // 4. Latency Degradation
  const mult = Number(metrics.latency_multiplier || 1.0);
  if (metrics.degraded || mult > 1.0) {
    return {
      status: 'DEGRADED',
      label: `DEGRADED (${mult}x)`,
      badgeBg: '#e65100',
      badgeBorder: '#ffa726',
      icon: '📉',
    };
  }

  // 5. Overloaded (High utilization or full queue)
  const util = Number(metrics.utilization || 0);
  const qDepth = Number(metrics.queue_depth || 0);
  const maxQ = Number(metrics.max_queue_depth || metrics.max_depth || 0);
  const isQueueFull = maxQ > 0 && qDepth >= maxQ * 0.9;

  if (util >= 0.95 || isQueueFull) {
    return {
      status: 'OVERLOADED',
      label: 'OVERLOADED',
      badgeBg: '#880e4f',
      badgeBorder: '#ad1457',
      icon: '🔥',
    };
  }

  // 6. Healthy
  return {
    status: 'HEALTHY',
    label: 'HEALTHY',
    badgeBg: '#1b5e20',
    badgeBorder: '#43a047',
    icon: '🟢',
  };
}

export function InfrastructureNode({ data, selected }: NodeProps) {
  const m = data.metrics;
  const health = determineNodeHealth(m);

  let utilPercent = 0;
  if (m && m.capacity && m.capacity > 0) {
    utilPercent = Math.min(100, Math.max(0, ((m.active || 0) / m.capacity) * 100));
  } else if (m && m.utilization !== undefined) {
    utilPercent = Math.min(100, Math.max(0, m.utilization * 100));
  }

  let queuePercent = 0;
  const maxQ = m?.max_queue_depth || m?.max_depth || 0;
  if (m && m.queue_depth !== undefined && maxQ > 0) {
    queuePercent = Math.min(100, (m.queue_depth / maxQ) * 100);
  }

  return (
    <div className={`custom-node ${data.type || 'unknown'} ${selected ? 'node-selected' : ''}`}>
      <Handle type="target" position={Position.Top} />

      {/* Node Header with Type & Explicit Health Badge (Color + Text) */}
      <div className="node-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 600 }}>{data.label}</span>
          <span
            className="node-health-badge"
            style={{
              backgroundColor: health.badgeBg,
              borderColor: health.badgeBorder,
            }}
            title={`Health State: ${health.label}`}
          >
            <span style={{ marginRight: 3, fontSize: '0.65rem' }}>{health.icon}</span>
            {health.label}
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: '#90caf9', marginTop: 2 }}>
          {data.type?.toUpperCase()}
        </div>
      </div>

      {/* Gauges & Telemetry */}
      {m ? (
        <div className="node-body">
          {/* Concurrency Utilization Bar */}
          {m.capacity !== undefined && (
            <div style={{ marginBottom: 4 }}>
              <div className="node-metric-row">
                <span>Workers:</span>
                <span>
                  {m.active || 0}/{m.capacity} ({utilPercent.toFixed(0)}%)
                </span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${utilPercent}%`,
                    backgroundColor:
                      utilPercent > 90 ? '#ef5350' : utilPercent > 70 ? '#ffa726' : '#66bb6a',
                  }}
                />
              </div>
            </div>
          )}

          {/* Queue Depth Bar */}
          {m.queue_depth !== undefined && maxQ > 0 && (
            <div style={{ marginBottom: 4 }}>
              <div className="node-metric-row">
                <span>Queue:</span>
                <span>
                  {m.queue_depth}/{maxQ}
                </span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${queuePercent}%`,
                    backgroundColor:
                      queuePercent > 85 ? '#ef5350' : queuePercent > 50 ? '#ffb74d' : '#29b6f6',
                  }}
                />
              </div>
            </div>
          )}

          {/* Readout Grid */}
          <div className="node-telemetry-grid">
            {m.throughput !== undefined && (
              <div>
                <span className="telemetry-label">Thp:</span> {Number(m.throughput).toFixed(1)}/s
              </div>
            )}
            {m.latency_p95 !== undefined && (
              <div>
                <span className="telemetry-label">p95:</span> {(m.latency_p95 * 1000).toFixed(0)}ms
              </div>
            )}
            {m.completed !== undefined && (
              <div>
                <span className="telemetry-label">Done:</span> {m.completed}
              </div>
            )}
            {m.dropped !== undefined && (
              <div style={{ color: m.dropped > 0 ? '#ef5350' : 'inherit' }}>
                <span className="telemetry-label">Drop:</span> {m.dropped}
              </div>
            )}
            {m.hits !== undefined && (
              <div>
                <span className="telemetry-label">Hit%:</span>{' '}
                {((m.hits / ((m.hits + m.misses) || 1)) * 100).toFixed(0)}%
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ fontSize: '0.72rem', color: '#888', marginTop: 4, fontStyle: 'italic' }}>
          Ready for simulation
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
