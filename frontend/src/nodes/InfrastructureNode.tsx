import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export function InfrastructureNode({ data, type, id }: NodeProps) {
  const m = data.metrics;
  
  let util = 0;
  if (m && m.capacity && m.capacity > 0) {
    util = (m.active / m.capacity) * 100;
  }

  return (
    <div className={`custom-node ${data.type || 'unknown'}`}>
      <Handle type="target" position={Position.Top} />
      <div className="node-header">
        {data.label}
        <div style={{fontSize: '0.8em', color: '#aaa'}}>{data.type}</div>
      </div>
      
      {m && (
        <div style={{ marginTop: 10, fontSize: '0.8em', textAlign: 'left' }}>
          {m.capacity && (
            <div style={{ background: '#ddd', height: '5px', width: '100%' }}>
              <div style={{ background: util > 80 ? 'red' : 'green', height: '5px', width: `${Math.min(util, 100)}%` }} />
            </div>
          )}
          {m.queue_depth !== undefined && (
            <div style={{ background: '#ddd', height: '5px', width: '100%' }}>
              <div style={{ background: 'orange', height: '5px', width: `${Math.min((m.queue_depth/m.max_depth)*100, 100)}%` }} />
            </div>
          )}
          {m.completed !== undefined && <div>Comp: {m.completed}</div>}
          {m.dropped !== undefined && <div>Drop: {m.dropped}</div>}
          {m.active !== undefined && <div>Act: {m.active}</div>}
          {m.hits !== undefined && <div>Hits: {m.hits}</div>}
          {m.misses !== undefined && <div>Misses: {m.misses}</div>}
          {m.queue_depth !== undefined && <div>Q-Depth: {m.queue_depth}</div>}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
