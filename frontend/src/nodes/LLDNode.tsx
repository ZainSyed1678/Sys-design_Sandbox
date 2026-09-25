import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export interface LLDAttribute {
  id: string;
  visibility: '+' | '-' | '#';
  name: string;
  type: string;
}

export interface LLDMethod {
  id: string;
  visibility: '+' | '-' | '#';
  name: string;
  params: string;
  returnType: string;
}

export interface LLDNodeData {
  label: string;
  stereotype: 'class' | 'interface' | 'service' | 'repository' | 'controller' | 'pattern';
  patternType?: string;
  attributes: LLDAttribute[];
  methods: LLDMethod[];
}

export function LLDNode({ data, selected }: NodeProps<LLDNodeData>) {
  const stereotypeLabel = data.stereotype === 'interface' 
    ? '<<interface>>' 
    : data.stereotype === 'pattern'
    ? `<<${data.patternType || 'Pattern'}>>`
    : `<<${data.stereotype}>>`;

  return (
    <div className={`lld-node ${data.stereotype} ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} className="lld-handle" />
      <Handle type="target" position={Position.Left} id="left-target" className="lld-handle" />
      
      <div className="lld-header">
        <span className="lld-stereotype">{stereotypeLabel}</span>
        <span className="lld-title">{data.label}</span>
      </div>

      {data.attributes && data.attributes.length > 0 && (
        <div className="lld-section lld-attributes">
          {data.attributes.map((attr: LLDAttribute) => (
            <div key={attr.id} className="lld-item">
              <span className="lld-vis">{attr.visibility}</span>
              <span className="lld-name">{attr.name}</span>: <span className="lld-type">{attr.type}</span>
            </div>
          ))}
        </div>
      )}

      {data.methods && data.methods.length > 0 && (
        <div className="lld-section lld-methods">
          {data.methods.map((method: LLDMethod) => (
            <div key={method.id} className="lld-item">
              <span className="lld-vis">{method.visibility}</span>
              <span className="lld-name">{method.name}</span>({method.params}): <span className="lld-type">{method.returnType}</span>
            </div>
          ))}
        </div>
      )}

      <Handle type="source" position={Position.Right} id="right-source" className="lld-handle" />
      <Handle type="source" position={Position.Bottom} className="lld-handle" />
    </div>
  );
}
