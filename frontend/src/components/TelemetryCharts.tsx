import React, { useState, useMemo } from 'react';

interface HistoryPoint {
  time?: number;
  window_idx?: number;
  window_start?: number;
  throughput?: number;
  drop_rate?: number;
  latency_p50?: number;
  latency_p95?: number;
  latency_p99?: number;
  latency_mean?: number;
  queue_depth?: number;
  utilization?: number;
}

interface TelemetryChartsProps {
  selectedNodeId: string | null;
  selectedNodeLabel?: string;
  selectedNodeMetrics?: any;
  systemMetrics: any;
  systemHistory: HistoryPoint[];
  onClearSelection?: () => void;
}

export function TelemetryCharts({
  selectedNodeId,
  selectedNodeLabel,
  selectedNodeMetrics,
  systemMetrics,
  systemHistory,
  onClearSelection,
}: TelemetryChartsProps) {
  const [metricTab, setMetricTab] = useState<'latency' | 'throughput' | 'queue_util'>('latency');

  // Determine whether showing component telemetry or global system telemetry
  const isComponentMode = Boolean(selectedNodeId && selectedNodeMetrics);
  const title = isComponentMode
    ? `Component Telemetry: ${selectedNodeLabel || selectedNodeId}`
    : 'System-Wide Telemetry (Aggregated)';

  const history: HistoryPoint[] = useMemo(() => {
    if (isComponentMode && selectedNodeMetrics?.history && selectedNodeMetrics.history.length > 0) {
      return selectedNodeMetrics.history;
    }
    return systemHistory || [];
  }, [isComponentMode, selectedNodeMetrics, systemHistory]);

  const latestStats = useMemo(() => {
    const src = isComponentMode ? selectedNodeMetrics : systemMetrics;
    if (!src) return { p50: 0, p95: 0, p99: 0, thp: 0, drop: 0, util: 0, q: 0 };
    return {
      p50: Number(src.latency_p50 || 0),
      p95: Number(src.latency_p95 || 0),
      p99: Number(src.latency_p99 || 0),
      thp: Number(src.throughput || 0),
      drop: Number(src.drop_rate || 0),
      util: Number(src.utilization !== undefined ? src.utilization : src.system_utilization || 0),
      q: Number(src.queue_depth || src.mean_queue_length || 0),
    };
  }, [isComponentMode, selectedNodeMetrics, systemMetrics]);

  // SVG Chart rendering dimensions
  const width = 360;
  const height = 140;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  // Extract series based on current tab
  const chartData = useMemo(() => {
    if (!history || history.length < 2) return null;

    let series1: number[] = [];
    let series2: number[] = [];
    let series3: number[] = [];
    let s1Label = '';
    let s2Label = '';
    let s3Label = '';
    let s1Color = '#42a5f5';
    let s2Color = '#ffa726';
    let s3Color = '#ef5350';
    let unit = '';

    if (metricTab === 'latency') {
      s1Label = 'p50';
      s2Label = 'p95';
      s3Label = 'p99';
      s1Color = '#66bb6a'; // green
      s2Color = '#ffa726'; // amber
      s3Color = '#ef5350'; // red
      unit = 's';
      series1 = history.map((h) => Number(h.latency_p50 || 0));
      series2 = history.map((h) => Number(h.latency_p95 || 0));
      series3 = history.map((h) => Number(h.latency_p99 || 0));
    } else if (metricTab === 'throughput') {
      s1Label = 'Throughput (req/s)';
      s2Label = 'Drop Rate (%)';
      s1Color = '#42a5f5';
      s2Color = '#e91e63';
      unit = 'req/s';
      series1 = history.map((h) => Number(h.throughput || 0));
      series2 = history.map((h) => Number((h.drop_rate || 0) * 100));
    } else {
      s1Label = 'Utilization (%)';
      s2Label = 'Queue Depth';
      s1Color = '#ab47bc';
      s2Color = '#26c6da';
      unit = '%';
      series1 = history.map((h) => Number((h.utilization || 0) * 100));
      series2 = history.map((h) => Number(h.queue_depth || 0));
    }

    const allValues = [...series1, ...series2, ...series3];
    const maxVal = Math.max(0.01, ...allValues);
    const minVal = 0;

    const getPolyline = (pts: number[]) => {
      return pts
        .map((val, idx) => {
          const x = padding.left + (idx / (pts.length - 1)) * plotW;
          const y = padding.top + plotH - ((val - minVal) / (maxVal - minVal || 1)) * plotH;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(' ');
    };

    return {
      polyline1: getPolyline(series1),
      polyline2: series2.length ? getPolyline(series2) : '',
      polyline3: series3.length ? getPolyline(series3) : '',
      s1Label,
      s2Label,
      s3Label,
      s1Color,
      s2Color,
      s3Color,
      maxVal,
      unit,
      count: history.length,
    };
  }, [history, metricTab]);

  return (
    <div className="telemetry-panel">
      {/* Telemetry Header */}
      <div className="telemetry-header">
        <div>
          <div className="telemetry-subtitle">
            {isComponentMode ? 'TARGET COMPONENT' : 'AGGREGATE TOPOLOGY'}
          </div>
          <h3 className="telemetry-title">{title}</h3>
        </div>
        {isComponentMode && onClearSelection && (
          <button onClick={onClearSelection} className="telemetry-reset-btn" title="View Whole System Telemetry">
            Global Overview
          </button>
        )}
      </div>

      {/* KPI Summary Cards */}
      <div className="telemetry-kpis">
        <div className="telemetry-kpi-card">
          <div className="kpi-label">p50 / p95 / p99 Latency</div>
          <div className="kpi-val" style={{ color: '#90caf9' }}>
            {(latestStats.p50 * 1000).toFixed(0)} / {(latestStats.p95 * 1000).toFixed(0)} /{' '}
            {(latestStats.p99 * 1000).toFixed(0)}{' '}
            <span style={{ fontSize: '0.7rem', color: '#aaa' }}>ms</span>
          </div>
        </div>

        <div className="telemetry-kpi-card">
          <div className="kpi-label">Throughput / Drops</div>
          <div className="kpi-val" style={{ color: '#81c784' }}>
            {latestStats.thp.toFixed(1)}{' '}
            <span style={{ fontSize: '0.7rem', color: '#aaa' }}>req/s</span>
            <span
              style={{
                marginLeft: 6,
                fontSize: '0.75rem',
                color: latestStats.drop > 0 ? '#ef5350' : '#81c784',
              }}
            >
              ({(latestStats.drop * 100).toFixed(1)}% drop)
            </span>
          </div>
        </div>

        <div className="telemetry-kpi-card">
          <div className="kpi-label">Utilization / Queue</div>
          <div className="kpi-val" style={{ color: '#ce93d8' }}>
            {(latestStats.util * 100).toFixed(1)}%
            <span style={{ marginLeft: 6, fontSize: '0.75rem', color: '#80deea' }}>
              (Q: {latestStats.q.toFixed(0)})
            </span>
          </div>
        </div>
      </div>

      {/* Metric Selector Tabs */}
      <div className="telemetry-tabs">
        <button
          className={`telemetry-tab-btn ${metricTab === 'latency' ? 'active' : ''}`}
          onClick={() => setMetricTab('latency')}
        >
          Latency Percentiles
        </button>
        <button
          className={`telemetry-tab-btn ${metricTab === 'throughput' ? 'active' : ''}`}
          onClick={() => setMetricTab('throughput')}
        >
          Throughput & Drops
        </button>
        <button
          className={`telemetry-tab-btn ${metricTab === 'queue_util' ? 'active' : ''}`}
          onClick={() => setMetricTab('queue_util')}
        >
          Queue & Utilization
        </button>
      </div>

      {/* Live SVG Chart */}
      <div className="telemetry-chart-container">
        {chartData ? (
          <div>
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="telemetry-svg"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Reference Gridlines */}
              <line
                x1={padding.left}
                y1={padding.top}
                x2={width - padding.right}
                y2={padding.top}
                stroke="#3a3a48"
                strokeDasharray="3 3"
              />
              <line
                x1={padding.left}
                y1={padding.top + plotH / 2}
                x2={width - padding.right}
                y2={padding.top + plotH / 2}
                stroke="#3a3a48"
                strokeDasharray="3 3"
              />
              <line
                x1={padding.left}
                y1={padding.top + plotH}
                x2={width - padding.right}
                y2={padding.top + plotH}
                stroke="#4a4a58"
              />
              <line
                x1={padding.left}
                y1={padding.top}
                x2={padding.left}
                y2={padding.top + plotH}
                stroke="#4a4a58"
              />

              {/* Y-Axis Labels */}
              <text
                x={padding.left - 4}
                y={padding.top + 4}
                fill="#888"
                fontSize="9"
                textAnchor="end"
              >
                {chartData.maxVal >= 10 ? chartData.maxVal.toFixed(0) : chartData.maxVal.toFixed(2)}
              </text>
              <text
                x={padding.left - 4}
                y={padding.top + plotH / 2 + 3}
                fill="#888"
                fontSize="9"
                textAnchor="end"
              >
                {(chartData.maxVal / 2).toFixed(1)}
              </text>
              <text
                x={padding.left - 4}
                y={padding.top + plotH}
                fill="#888"
                fontSize="9"
                textAnchor="end"
              >
                0
              </text>

              {/* Polylines */}
              {chartData.polyline1 && (
                <polyline
                  fill="none"
                  stroke={chartData.s1Color}
                  strokeWidth="2"
                  points={chartData.polyline1}
                />
              )}
              {chartData.polyline2 && (
                <polyline
                  fill="none"
                  stroke={chartData.s2Color}
                  strokeWidth="2"
                  points={chartData.polyline2}
                />
              )}
              {chartData.polyline3 && (
                <polyline
                  fill="none"
                  stroke={chartData.s3Color}
                  strokeWidth="2"
                  points={chartData.polyline3}
                />
              )}

              {/* X-Axis Time Label */}
              <text
                x={width - padding.right}
                y={height - 5}
                fill="#888"
                fontSize="9"
                textAnchor="end"
              >
                Live Timeline (last {chartData.count}s)
              </text>
            </svg>

            {/* Chart Legend */}
            <div className="telemetry-legend">
              <span style={{ color: chartData.s1Color }}>
                ■ <strong>{chartData.s1Label}</strong>
              </span>
              {chartData.s2Label && (
                <span style={{ color: chartData.s2Color }}>
                  ■ <strong>{chartData.s2Label}</strong>
                </span>
              )}
              {chartData.s3Label && (
                <span style={{ color: chartData.s3Color }}>
                  ■ <strong>{chartData.s3Label}</strong>
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="telemetry-empty">
            <span style={{ fontSize: '1.2rem', marginBottom: 4 }}>📈</span>
            <div>Awaiting simulation telemetry...</div>
            <div style={{ fontSize: '0.75rem', color: '#666' }}>
              Start simulation to stream server-aggregated time series.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
