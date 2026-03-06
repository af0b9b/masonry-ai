"use client";

import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";

const nodes = [
  { id: "gate", position: { x: 0, y: 0 }, data: { label: "Gatekeeper" }, type: "default" },
  { id: "engine", position: { x: 220, y: 0 }, data: { label: "Engine" }, type: "default" },
  { id: "api", position: { x: 440, y: 0 }, data: { label: "API" }, type: "default" }
];

const edges = [
  { id: "e1", source: "gate", target: "engine" },
  { id: "e2", source: "engine", target: "api" }
];

export function DecisionGraph() {
  return (
    <div style={{ height: 360, border: "1px solid #d8d8d8" }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
