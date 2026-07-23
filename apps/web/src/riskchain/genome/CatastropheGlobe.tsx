"use client";

import { Html, Line, OrbitControls, Stars } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";

export type GlobeEntry = {
  id: string;
  name: string;
  subtitle: string;
  center: [number, number];
  color: string;
  height?: number;
  detail: string;
};

type Props = {
  entries: GlobeEntry[];
  selectedId?: string | null;
  onSelect: (entry: GlobeEntry) => void;
  autoRotate: boolean;
};

const RADIUS = 1.7;

function toGlobePosition([longitude, latitude]: [number, number], radius = RADIUS) {
  const phi = (90 - latitude) * (Math.PI / 180);
  const theta = (longitude + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function Graticule() {
  const latitudeLines = useMemo(() => [-60, -30, 0, 30, 60].map((latitude) => {
    const points = Array.from({ length: 97 }, (_, index) => toGlobePosition([-180 + index * 3.75, latitude], RADIUS + 0.004));
    return { id: `latitude-${latitude}`, points };
  }), []);
  const longitudeLines = useMemo(() => [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150].map((longitude) => {
    const points = Array.from({ length: 73 }, (_, index) => toGlobePosition([longitude, -90 + index * 2.5], RADIUS + 0.005));
    return { id: `longitude-${longitude}`, points };
  }), []);
  return <group>
    {latitudeLines.map((line) => <Line key={line.id} points={line.points} color="#557398" transparent opacity={0.24} lineWidth={0.65} />)}
    {longitudeLines.map((line) => <Line key={line.id} points={line.points} color="#557398" transparent opacity={0.18} lineWidth={0.55} />)}
  </group>;
}

function Beacon({ entry, selected, onSelect }: { entry: GlobeEntry; selected: boolean; onSelect: (entry: GlobeEntry) => void }) {
  const { point, quaternion, height } = useMemo(() => {
    const point = toGlobePosition(entry.center, RADIUS + 0.02);
    const normal = point.clone().normalize();
    const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
    return { point, quaternion, height: entry.height ?? 0.12 };
  }, [entry.center, entry.height]);
  // The visual marker has a deliberately large hit target. OrbitControls still
  // handles background drags; a direct marker click opens the source-backed card.
  return <group position={point} quaternion={quaternion}>
    <mesh
      position={[0, height / 2, 0]}
      onClick={(event) => { event.stopPropagation(); onSelect(entry); }}
    >
      <cylinderGeometry args={[0.012, 0.024, height, 8]} />
      <meshBasicMaterial color={entry.color} transparent opacity={0.9} />
    </mesh>
    <mesh
      position={[0, height + 0.038, 0]}
      onClick={(event) => { event.stopPropagation(); onSelect(entry); }}
    >
      <sphereGeometry args={[selected ? 0.095 : 0.058, 16, 16]} />
      <meshBasicMaterial color={entry.color} />
    </mesh>
    {selected && <>
      <mesh position={[0, height + 0.038, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.115, 0.132, 32]} />
        <meshBasicMaterial color="#F2F7FB" transparent opacity={0.9} side={THREE.DoubleSide} />
      </mesh>
      <Html transform position={[0, height + 0.21, 0]} distanceFactor={7.8} style={{ pointerEvents: "none" }}>
        <div className="globe-marker-label"><strong>{entry.name}</strong><span>{entry.subtitle}</span></div>
      </Html>
    </>}
  </group>;
}

function GlobeScene({ entries, selectedId, onSelect, autoRotate }: Props) {
  return <>
    <color attach="background" args={["#08111f"]} />
    <fog attach="fog" args={["#08111f", 5, 13]} />
    <ambientLight intensity={0.75} color="#9fc8e8" />
    <pointLight position={[4, 3, 5]} intensity={14} color="#8fd2ff" />
    <pointLight position={[-4, -2, 2]} intensity={7} color="#ff8a3d" />
    <Stars radius={70} depth={30} count={1200} factor={2} saturation={0} fade speed={0.3} />
    <group rotation={[0.08, -0.58, 0]}>
      <mesh>
        <sphereGeometry args={[RADIUS, 64, 64]} />
        <meshStandardMaterial color="#10253c" metalness={0.35} roughness={0.5} transparent opacity={0.93} />
      </mesh>
      <mesh scale={1.015}>
        <sphereGeometry args={[RADIUS, 64, 64]} />
        <meshBasicMaterial color="#3b93c9" transparent opacity={0.07} side={THREE.BackSide} />
      </mesh>
      <Graticule />
      {entries.map((entry) => <Beacon key={entry.id} entry={entry} selected={entry.id === selectedId} onSelect={onSelect} />)}
    </group>
    <OrbitControls
      enablePan={false}
      minDistance={3.6}
      maxDistance={8.5}
      autoRotate={autoRotate}
      autoRotateSpeed={0.45}
      rotateSpeed={0.55}
      zoomSpeed={0.7}
    />
  </>;
}

export function CatastropheGlobe({ entries, selectedId, onSelect, autoRotate }: Props) {
  return <div className="catastrophe-globe" role="img" aria-label="Interactive three-dimensional globe of catastrophe event reference locations. Drag to orbit, scroll to zoom, and select a beacon for details.">
    <Canvas camera={{ position: [0, 0.25, 5.65], fov: 42 }} dpr={[1, 1.6]} gl={{ antialias: true, powerPreference: "high-performance" }}>
      <GlobeScene entries={entries} selectedId={selectedId} onSelect={onSelect} autoRotate={autoRotate} />
    </Canvas>
    <div className="globe-gesture-hint">Drag to orbit · scroll to zoom · select a beacon</div>
  </div>;
}
