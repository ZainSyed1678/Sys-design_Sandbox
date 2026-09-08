import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export function InfrastructureNode({ data, type }: NodeProps) {
  return (
    <div className={`custom-node ${data.type || 'unknown'}`}>
      <Handle type="target" position={Position.Top} />
      <div>
        {data.label}
        <br/>
        <small>{data.type}</small>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
