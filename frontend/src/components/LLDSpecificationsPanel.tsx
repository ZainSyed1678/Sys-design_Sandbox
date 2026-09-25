import React, { useState } from 'react';
import { Node } from 'reactflow';
import { LLDNodeData, LLDAttribute, LLDMethod } from '../nodes/LLDNode';

interface Props {
  node: Node<LLDNodeData>;
  onUpdate: (updatedNode: Node<LLDNodeData>) => void;
  onClose: () => void;
}

export function LLDSpecificationsPanel({ node, onUpdate, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'specs' | 'code'>('specs');
  const [codeLang, setCodeLang] = useState<'typescript' | 'python'>('typescript');

  // Form states for new attribute
  const [newAttrVis, setNewAttrVis] = useState<'+' | '-' | '#'>('-');
  const [newAttrName, setNewAttrName] = useState('');
  const [newAttrType, setNewAttrType] = useState('string');

  // Form states for new method
  const [newMethodVis, setNewMethodVis] = useState<'+' | '-' | '#'>('+');
  const [newMethodName, setNewMethodName] = useState('');
  const [newMethodParams, setNewMethodParams] = useState('');
  const [newMethodReturn, setNewMethodReturn] = useState('void');

  const updateData = (partial: Partial<LLDNodeData>) => {
    onUpdate({
      ...node,
      data: {
        ...node.data,
        ...partial,
      },
    });
  };

  const handleAddAttribute = () => {
    if (!newAttrName.trim()) return;
    const newAttr: LLDAttribute = {
      id: `attr_${Date.now()}`,
      visibility: newAttrVis,
      name: newAttrName.trim(),
      type: newAttrType.trim() || 'any',
    };
    updateData({
      attributes: [...(node.data.attributes || []), newAttr],
    });
    setNewAttrName('');
  };

  const handleRemoveAttribute = (id: string) => {
    updateData({
      attributes: node.data.attributes.filter((a) => a.id !== id),
    });
  };

  const handleAddMethod = () => {
    if (!newMethodName.trim()) return;
    const newMethod: LLDMethod = {
      id: `meth_${Date.now()}`,
      visibility: newMethodVis,
      name: newMethodName.trim(),
      params: newMethodParams.trim(),
      returnType: newMethodReturn.trim() || 'void',
    };
    updateData({
      methods: [...(node.data.methods || []), newMethod],
    });
    setNewMethodName('');
    setNewMethodParams('');
  };

  const handleRemoveMethod = (id: string) => {
    updateData({
      methods: node.data.methods.filter((m) => m.id !== id),
    });
  };

  const generateCode = () => {
    const { label, stereotype, patternType, attributes, methods } = node.data;
    const isInterface = stereotype === 'interface';

    if (codeLang === 'typescript') {
      let code = '';
      if (patternType) {
        code += `// Pattern: ${patternType}\n`;
      }
      if (isInterface) {
        code += `export interface ${label} {\n`;
        attributes.forEach((a) => {
          code += `  ${a.name}: ${a.type};\n`;
        });
        methods.forEach((m) => {
          code += `  ${m.name}(${m.params}): ${m.returnType};\n`;
        });
        code += `}\n`;
      } else {
        code += `export class ${label} {\n`;
        attributes.forEach((a) => {
          const vis = a.visibility === '-' ? 'private' : a.visibility === '#' ? 'protected' : 'public';
          code += `  ${vis} ${a.name}: ${a.type};\n`;
        });
        if (attributes.length > 0) {
          code += `\n  constructor(\n`;
          attributes.forEach((a) => {
            code += `    ${a.name}: ${a.type},\n`;
          });
          code += `  ) {\n`;
          attributes.forEach((a) => {
            code += `    this.${a.name} = ${a.name};\n`;
          });
          code += `  }\n`;
        }
        methods.forEach((m) => {
          const vis = m.visibility === '-' ? 'private' : m.visibility === '#' ? 'protected' : 'public';
          code += `\n  ${vis} ${m.name}(${m.params}): ${m.returnType} {\n`;
          code += `    // TODO: implement ${m.name}\n`;
          if (m.returnType !== 'void') {
            code += `    throw new Error('Not implemented');\n`;
          }
          code += `  }\n`;
        });
        code += `}\n`;
      }
      return code;
    } else {
      // Python code
      let code = '';
      if (isInterface) {
        code += `from abc import ABC, abstractmethod\n\n`;
        code += `class ${label}(ABC):\n`;
        if (methods.length === 0) {
          code += `    pass\n`;
        }
        methods.forEach((m) => {
          const p = m.params ? `self, ${m.params}` : 'self';
          code += `    @abstractmethod\n`;
          code += `    def ${m.name}(${p}) -> ${m.returnType}:\n`;
          code += `        pass\n\n`;
        });
      } else {
        code += `class ${label}:\n`;
        if (attributes.length > 0) {
          const p = attributes.map((a) => `${a.name}: ${a.type}`).join(', ');
          code += `    def __init__(self, ${p}):\n`;
          attributes.forEach((a) => {
            const prefix = a.visibility === '-' ? '__' : a.visibility === '#' ? '_' : '';
            code += `        self.${prefix}${a.name} = ${a.name}\n`;
          });
          code += `\n`;
        }
        if (methods.length === 0 && attributes.length === 0) {
          code += `    pass\n`;
        }
        methods.forEach((m) => {
          const prefix = m.visibility === '-' ? '__' : m.visibility === '#' ? '_' : '';
          const p = m.params ? `self, ${m.params}` : 'self';
          code += `    def ${prefix}${m.name}(${p}) -> ${m.returnType}:\n`;
          code += `        # TODO: implement\n`;
          code += `        pass\n\n`;
        });
      }
      return code;
    }
  };

  return (
    <div className="spec-panel">
      <div className="spec-header">
        <div>
          <h3 style={{ margin: 0, color: '#64b5f6' }}>Specifications</h3>
          <span style={{ fontSize: '0.8rem', color: '#aaa' }}>{node.data.label} ({node.data.stereotype})</span>
        </div>
        <button onClick={onClose} className="spec-close-btn">&times;</button>
      </div>

      <div className="spec-tabs">
        <button 
          className={`spec-tab-btn ${activeTab === 'specs' ? 'active' : ''}`}
          onClick={() => setActiveTab('specs')}
        >
          Properties & Contract
        </button>
        <button 
          className={`spec-tab-btn ${activeTab === 'code' ? 'active' : ''}`}
          onClick={() => setActiveTab('code')}
        >
          Code Preview
        </button>
      </div>

      {activeTab === 'specs' ? (
        <div className="spec-body">
          {/* General Properties */}
          <div className="spec-group">
            <label>Component Name</label>
            <input 
              type="text" 
              className="spec-input"
              value={node.data.label} 
              onChange={(e) => updateData({ label: e.target.value })}
            />
          </div>

          <div className="spec-group">
            <label>Stereotype / Archetype</label>
            <select 
              className="spec-select"
              value={node.data.stereotype} 
              onChange={(e) => updateData({ stereotype: e.target.value as any })}
            >
              <option value="class">Class</option>
              <option value="interface">Interface</option>
              <option value="service">Service</option>
              <option value="repository">Repository</option>
              <option value="controller">Controller</option>
              <option value="pattern">Design Pattern</option>
            </select>
          </div>

          {node.data.stereotype === 'pattern' && (
            <div className="spec-group">
              <label>Pattern Type</label>
              <input 
                type="text" 
                className="spec-input"
                placeholder="e.g. Strategy, Factory, Observer"
                value={node.data.patternType || ''} 
                onChange={(e) => updateData({ patternType: e.target.value })}
              />
            </div>
          )}

          {/* Attributes */}
          <div className="spec-section">
            <h4>Fields / Attributes ({node.data.attributes?.length || 0})</h4>
            <div className="spec-items-list">
              {node.data.attributes && node.data.attributes.map((attr) => (
                <div key={attr.id} className="spec-item-row">
                  <span><strong>{attr.visibility}</strong> {attr.name}: <em>{attr.type}</em></span>
                  <button onClick={() => handleRemoveAttribute(attr.id)} className="spec-del-btn">✕</button>
                </div>
              ))}
              {(!node.data.attributes || node.data.attributes.length === 0) && (
                <p className="spec-empty">No attributes specified yet.</p>
              )}
            </div>

            <div className="spec-add-form">
              <select 
                value={newAttrVis} 
                onChange={(e) => setNewAttrVis(e.target.value as any)}
                className="spec-select-sm"
              >
                <option value="-">- (private)</option>
                <option value="+">+ (public)</option>
                <option value="#"># (protected)</option>
              </select>
              <input 
                type="text" 
                placeholder="fieldName" 
                className="spec-input-sm"
                value={newAttrName}
                onChange={(e) => setNewAttrName(e.target.value)}
              />
              <input 
                type="text" 
                placeholder="type" 
                className="spec-input-sm"
                value={newAttrType}
                onChange={(e) => setNewAttrType(e.target.value)}
              />
              <button onClick={handleAddAttribute} className="spec-add-btn">+ Add</button>
            </div>
          </div>

          {/* Methods */}
          <div className="spec-section">
            <h4>Methods & Operations ({node.data.methods?.length || 0})</h4>
            <div className="spec-items-list">
              {node.data.methods && node.data.methods.map((m) => (
                <div key={m.id} className="spec-item-row">
                  <span><strong>{m.visibility}</strong> {m.name}({m.params}): <em>{m.returnType}</em></span>
                  <button onClick={() => handleRemoveMethod(m.id)} className="spec-del-btn">✕</button>
                </div>
              ))}
              {(!node.data.methods || node.data.methods.length === 0) && (
                <p className="spec-empty">No methods specified yet.</p>
              )}
            </div>

            <div className="spec-add-form">
              <select 
                value={newMethodVis} 
                onChange={(e) => setNewMethodVis(e.target.value as any)}
                className="spec-select-sm"
              >
                <option value="+">+ (public)</option>
                <option value="-">- (private)</option>
                <option value="#"># (protected)</option>
              </select>
              <input 
                type="text" 
                placeholder="methodName" 
                className="spec-input-sm"
                value={newMethodName}
                onChange={(e) => setNewMethodName(e.target.value)}
              />
              <input 
                type="text" 
                placeholder="params (e.g. id: string)" 
                className="spec-input-sm"
                value={newMethodParams}
                onChange={(e) => setNewMethodParams(e.target.value)}
              />
              <input 
                type="text" 
                placeholder="returnType" 
                className="spec-input-sm"
                value={newMethodReturn}
                onChange={(e) => setNewMethodReturn(e.target.value)}
              />
              <button onClick={handleAddMethod} className="spec-add-btn">+ Add</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="spec-body">
          <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
            <button 
              className={`spec-lang-btn ${codeLang === 'typescript' ? 'active' : ''}`}
              onClick={() => setCodeLang('typescript')}
            >
              TypeScript
            </button>
            <button 
              className={`spec-lang-btn ${codeLang === 'python' ? 'active' : ''}`}
              onClick={() => setCodeLang('python')}
            >
              Python
            </button>
          </div>
          <pre className="spec-code-block">
            <code>{generateCode()}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
