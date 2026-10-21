import React, { useState, useEffect } from 'react';
import { Node, Edge } from 'reactflow';

interface PropertiesPanelProps {
  selectedNode: Node | null;
  selectedEdge: Edge | null;
  onUpdateNode: (updatedNode: Node) => void;
  onUpdateEdge: (updatedEdge: Edge) => void;
  onClose: () => void;
}

export function PropertiesPanel({
  selectedNode,
  selectedEdge,
  onUpdateNode,
  onUpdateEdge,
  onClose,
}: PropertiesPanelProps) {
  // Node state fields
  const [label, setLabel] = useState('');
  const [concurrency, setConcurrency] = useState(10);
  const [latency, setLatency] = useState(0.1);
  const [distribution, setDistribution] = useState<'constant' | 'exponential' | 'lognormal'>('constant');
  const [maxQueueDepth, setMaxQueueDepth] = useState(50);

  // Resilience & Policies
  const [timeout, setTimeoutVal] = useState<string>('');
  const [hasRetries, setHasRetries] = useState(false);
  const [retries, setRetries] = useState(3);
  const [retryDelay, setRetryDelay] = useState(0.1);
  const [backoffType, setBackoffType] = useState<'exponential' | 'linear'>('exponential');
  const [retryBudget, setRetryBudget] = useState(0.2);

  const [hasCircuitBreaker, setHasCircuitBreaker] = useState(false);
  const [cbThreshold, setCbThreshold] = useState(5);
  const [cbRecoveryTimeout, setCbRecoveryTimeout] = useState(5.0);

  const [hasRateLimit, setHasRateLimit] = useState(false);
  const [rateLimitCapacity, setRateLimitCapacity] = useState(100);
  const [rateLimitRefill, setRateLimitRefill] = useState(50);

  // Type-specific fields
  const [ratePerSec, setRatePerSec] = useState(20);
  const [arrivalProcess, setArrivalProcess] = useState<'poisson' | 'constant'>('poisson');
  const [trafficPattern, setTrafficPattern] = useState<'constant' | 'poisson' | 'ramp' | 'step_spike' | 'diurnal' | 'bursty'>('constant');
  const [lbStrategy, setLbStrategy] = useState<'round_robin' | 'least_connections' | 'weighted' | 'random' | 'consistent_hashing'>('round_robin');
  const [hitRate, setHitRate] = useState(0.85);

  // Edge state fields
  const [edgeLabel, setEdgeLabel] = useState('');

  // Sync state when selectedNode changes
  useEffect(() => {
    if (selectedNode) {
      const d = selectedNode.data || {};
      setLabel(d.label || selectedNode.id);
      setConcurrency(Number(d.concurrency ?? d.capacity ?? 10));
      setLatency(Number(d.latency ?? 0.1));
      setDistribution(d.distribution || 'constant');
      setMaxQueueDepth(Number(d.max_queue_depth ?? 50));

      setTimeoutVal(d.timeout !== undefined ? String(d.timeout) : '');
      setHasRetries(Boolean(d.retries !== undefined));
      setRetries(Number(d.retries ?? 3));
      setRetryDelay(Number(d.retry_delay ?? 0.1));
      setBackoffType(d.backoff_type || 'exponential');
      setRetryBudget(Number(d.retry_budget ?? 0.2));

      setHasCircuitBreaker(Boolean(d.circuit_breaker));
      setCbThreshold(Number(d.cb_failure_threshold ?? 5));
      setCbRecoveryTimeout(Number(d.cb_recovery_timeout ?? 5.0));

      setHasRateLimit(Boolean(d.rate_limit));
      setRateLimitCapacity(Number(d.rate_limit_capacity ?? 100));
      setRateLimitRefill(Number(d.rate_limit_refill ?? 50));

      setRatePerSec(Number(d.rate_per_sec ?? 20));
      setArrivalProcess(d.arrival_process || 'poisson');
      setTrafficPattern(d.traffic_pattern || 'constant');
      setLbStrategy(d.strategy || 'round_robin');
      setHitRate(Number(d.hit_rate ?? 0.85));
    }
  }, [selectedNode]);

  // Sync state when selectedEdge changes
  useEffect(() => {
    if (selectedEdge) {
      setEdgeLabel(String(selectedEdge.label || ''));
    }
  }, [selectedEdge]);

  if (!selectedNode && !selectedEdge) return null;

  const handleSaveNode = () => {
    if (!selectedNode) return;
    const updatedData: any = {
      ...selectedNode.data,
      label: label.trim() || selectedNode.id,
      concurrency: Math.max(1, concurrency),
      latency: Math.max(0.0001, latency),
      distribution,
      max_queue_depth: Math.max(0, maxQueueDepth),
    };

    if (timeout.trim() !== '') {
      updatedData.timeout = Math.max(0.001, Number(timeout));
    } else {
      delete updatedData.timeout;
    }

    if (hasRetries) {
      updatedData.retries = Math.max(1, retries);
      updatedData.retry_delay = Math.max(0.001, retryDelay);
      updatedData.backoff_type = backoffType;
      updatedData.retry_budget = Math.min(1.0, Math.max(0.0, retryBudget));
    } else {
      delete updatedData.retries;
      delete updatedData.retry_delay;
      delete updatedData.backoff_type;
      delete updatedData.retry_budget;
    }

    if (hasCircuitBreaker) {
      updatedData.circuit_breaker = true;
      updatedData.cb_failure_threshold = Math.max(1, cbThreshold);
      updatedData.cb_recovery_timeout = Math.max(0.1, cbRecoveryTimeout);
    } else {
      delete updatedData.circuit_breaker;
    }

    if (hasRateLimit) {
      updatedData.rate_limit = true;
      updatedData.rate_limit_capacity = Math.max(1, rateLimitCapacity);
      updatedData.rate_limit_refill = Math.max(0.1, rateLimitRefill);
    } else {
      delete updatedData.rate_limit;
    }

    const ntype = selectedNode.data.type;
    if (ntype === 'client') {
      updatedData.rate_per_sec = Math.max(0.1, ratePerSec);
      updatedData.arrival_process = arrivalProcess;
      updatedData.traffic_pattern = trafficPattern;
    } else if (ntype === 'load_balancer') {
      updatedData.strategy = lbStrategy;
    } else if (ntype === 'cache' || ntype === 'cdn') {
      updatedData.hit_rate = Math.min(1.0, Math.max(0.0, hitRate));
    }

    onUpdateNode({
      ...selectedNode,
      data: updatedData,
    });
  };

  const handleSaveEdge = () => {
    if (!selectedEdge) return;
    onUpdateEdge({
      ...selectedEdge,
      label: edgeLabel.trim() || undefined,
    });
  };

  const nodeType = selectedNode?.data.type || 'component';

  return (
    <div className="properties-panel">
      <div className="properties-header">
        <div>
          <h3 style={{ margin: 0, color: '#64b5f6', fontSize: '1rem' }}>
            {selectedNode ? 'Component Settings' : 'Edge Configuration'}
          </h3>
          <span style={{ fontSize: '0.78rem', color: '#aaa' }}>
            {selectedNode ? `${label} (${nodeType.toUpperCase()})` : `Edge: ${selectedEdge?.id}`}
          </span>
        </div>
        <button onClick={onClose} className="properties-close-btn" aria-label="Close Properties">
          &times;
        </button>
      </div>

      <div className="properties-body">
        {selectedNode ? (
          <>
            {/* General Settings */}
            <div className="form-group">
              <label>Component Label</label>
              <input
                type="text"
                className="prop-input"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>

            {/* Client-specific traffic controls */}
            {nodeType === 'client' && (
              <div className="prop-section">
                <h4>Client Traffic Generator</h4>
                <div className="form-group">
                  <label>Arrival Rate (req/sec)</label>
                  <input
                    type="number"
                    min="0.1"
                    step="1"
                    className="prop-input"
                    value={ratePerSec}
                    onChange={(e) => setRatePerSec(Number(e.target.value))}
                  />
                </div>
                <div className="form-group">
                  <label>Arrival Stochastic Process</label>
                  <select
                    className="prop-select"
                    value={arrivalProcess}
                    onChange={(e) => setArrivalProcess(e.target.value as any)}
                  >
                    <option value="poisson">Poisson Process (Exponential inter-arrival)</option>
                    <option value="constant">Deterministic (Fixed rate)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Traffic Pattern Profile</label>
                  <select
                    className="prop-select"
                    value={trafficPattern}
                    onChange={(e) => setTrafficPattern(e.target.value as any)}
                  >
                    <option value="constant">Constant Load</option>
                    <option value="poisson">Poisson Random Fluctuation</option>
                    <option value="ramp">Linear Ramp-Up</option>
                    <option value="step_spike">Step Traffic Spike</option>
                    <option value="diurnal">Diurnal Sine Wave</option>
                    <option value="bursty">Bursty On/Off Spikes</option>
                  </select>
                </div>
              </div>
            )}

            {/* Load Balancer Specific */}
            {nodeType === 'load_balancer' && (
              <div className="prop-section">
                <h4>Routing Algorithm</h4>
                <div className="form-group">
                  <label>Load Balancing Strategy</label>
                  <select
                    className="prop-select"
                    value={lbStrategy}
                    onChange={(e) => setLbStrategy(e.target.value as any)}
                  >
                    <option value="round_robin">Round-Robin</option>
                    <option value="least_connections">Least-Connections</option>
                    <option value="weighted">Weighted Distribution</option>
                    <option value="random">Random Uniform</option>
                    <option value="consistent_hashing">Consistent Hashing (Ring)</option>
                  </select>
                </div>
              </div>
            )}

            {/* Cache Specific */}
            {(nodeType === 'cache' || nodeType === 'cdn') && (
              <div className="prop-section">
                <h4>Cache Performance</h4>
                <div className="form-group">
                  <label>Hit Ratio (0.0 to 1.0)</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    className="prop-input"
                    value={hitRate}
                    onChange={(e) => setHitRate(Number(e.target.value))}
                  />
                </div>
              </div>
            )}

            {/* Service & Concurrency (APIs, DBs, Workers) */}
            {['api', 'database', 'worker'].includes(nodeType) && (
              <div className="prop-section">
                <h4>Server Concurrency & Service Time</h4>
                <div className="form-group">
                  <label>Worker Concurrency (c)</label>
                  <input
                    type="number"
                    min="1"
                    className="prop-input"
                    value={concurrency}
                    onChange={(e) => setConcurrency(Number(e.target.value))}
                  />
                </div>
                <div className="form-group">
                  <label>Mean Service Duration (seconds)</label>
                  <input
                    type="number"
                    min="0.001"
                    step="0.01"
                    className="prop-input"
                    value={latency}
                    onChange={(e) => setLatency(Number(e.target.value))}
                  />
                </div>
                <div className="form-group">
                  <label>Service Time Distribution</label>
                  <select
                    className="prop-select"
                    value={distribution}
                    onChange={(e) => setDistribution(e.target.value as any)}
                  >
                    <option value="constant">Deterministic (Constant)</option>
                    <option value="exponential">M/M/c (Exponential)</option>
                    <option value="lognormal">Lognormal (Heavy-tailed)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Max Waiting Queue Depth (0 = drops when busy)</label>
                  <input
                    type="number"
                    min="0"
                    className="prop-input"
                    value={maxQueueDepth}
                    onChange={(e) => setMaxQueueDepth(Number(e.target.value))}
                  />
                </div>
              </div>
            )}

            {/* Resilience: Timeout, Retries, Breakers */}
            <div className="prop-section">
              <h4>Resilience & Fault Tolerance</h4>

              {/* Timeout */}
              <div className="form-group">
                <label>Request Timeout (seconds, blank for none)</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.1"
                  className="prop-input"
                  placeholder="e.g. 0.5"
                  value={timeout}
                  onChange={(e) => setTimeoutVal(e.target.value)}
                />
              </div>

              {/* Retries */}
              <div className="prop-checkbox-row">
                <input
                  type="checkbox"
                  id="enable-retries"
                  checked={hasRetries}
                  onChange={(e) => setHasRetries(e.target.checked)}
                />
                <label htmlFor="enable-retries">Enable Retries with Backoff</label>
              </div>
              {hasRetries && (
                <div className="prop-subform">
                  <div className="form-group">
                    <label>Max Retry Attempts</label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      className="prop-input"
                      value={retries}
                      onChange={(e) => setRetries(Number(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Base Delay (seconds)</label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.05"
                      className="prop-input"
                      value={retryDelay}
                      onChange={(e) => setRetryDelay(Number(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Backoff Algorithm</label>
                    <select
                      className="prop-select"
                      value={backoffType}
                      onChange={(e) => setBackoffType(e.target.value as any)}
                    >
                      <option value="exponential">Exponential with Full Jitter</option>
                      <option value="linear">Linear Backoff</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Retry Budget Ratio (0.0 to 1.0)</label>
                    <input
                      type="number"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      className="prop-input"
                      value={retryBudget}
                      onChange={(e) => setRetryBudget(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}

              {/* Circuit Breaker */}
              <div className="prop-checkbox-row">
                <input
                  type="checkbox"
                  id="enable-cb"
                  checked={hasCircuitBreaker}
                  onChange={(e) => setHasCircuitBreaker(e.target.checked)}
                />
                <label htmlFor="enable-cb">Enable Circuit Breaker</label>
              </div>
              {hasCircuitBreaker && (
                <div className="prop-subform">
                  <div className="form-group">
                    <label>Failure Threshold (consecutive failures)</label>
                    <input
                      type="number"
                      min="1"
                      className="prop-input"
                      value={cbThreshold}
                      onChange={(e) => setCbThreshold(Number(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Recovery Open Duration (seconds)</label>
                    <input
                      type="number"
                      min="0.1"
                      step="0.5"
                      className="prop-input"
                      value={cbRecoveryTimeout}
                      onChange={(e) => setCbRecoveryTimeout(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}

              {/* Token Bucket Rate Limiter */}
              <div className="prop-checkbox-row">
                <input
                  type="checkbox"
                  id="enable-tb"
                  checked={hasRateLimit}
                  onChange={(e) => setHasRateLimit(e.target.checked)}
                />
                <label htmlFor="enable-tb">Enable Token Bucket Load Shedding</label>
              </div>
              {hasRateLimit && (
                <div className="prop-subform">
                  <div className="form-group">
                    <label>Burst Capacity (Tokens)</label>
                    <input
                      type="number"
                      min="1"
                      className="prop-input"
                      value={rateLimitCapacity}
                      onChange={(e) => setRateLimitCapacity(Number(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Refill Rate (tokens/sec)</label>
                    <input
                      type="number"
                      min="1"
                      className="prop-input"
                      value={rateLimitRefill}
                      onChange={(e) => setRateLimitRefill(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}
            </div>

            <button onClick={handleSaveNode} className="prop-apply-btn">
              Apply Component Settings
            </button>
          </>
        ) : (
          /* Edge Properties */
          <>
            <div className="form-group">
              <label>Edge Label / Routing Path</label>
              <input
                type="text"
                className="prop-input"
                placeholder="e.g. routes /api/v1"
                value={edgeLabel}
                onChange={(e) => setEdgeLabel(e.target.value)}
              />
            </div>
            <button onClick={handleSaveEdge} className="prop-apply-btn">
              Apply Edge Settings
            </button>
          </>
        )}
      </div>
    </div>
  );
}
