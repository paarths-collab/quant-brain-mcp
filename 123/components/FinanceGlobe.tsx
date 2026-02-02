"use client";

import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import { useMemo, useRef, Suspense } from "react";
import * as THREE from "three";
import * as d3 from "d3-geo";

// Helper: Convert Lat/Lng to 3D Vector on Sphere
function latLngToVector3(lat: number, lng: number, radius: number) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);

    return [
        -radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta),
    ];
}

function CountryBorders() {
    const geo = useLoader(THREE.FileLoader, "/data/world.geo.json");

    const geometry = useMemo(() => {
        const geojson = JSON.parse(geo as string);
        const positions: number[] = [];
        const radius = 1.01; // Slightly above dot globe

        geojson.features.forEach((feature: any) => {
            const coords = feature.geometry.coordinates;
            const type = feature.geometry.type;

            const processPolygon = (polygon: any[]) => {
                polygon.forEach((ring: any[]) => {
                    for (let i = 0; i < ring.length - 1; i++) {
                        const [lng1, lat1] = ring[i];
                        const [lng2, lat2] = ring[i + 1];

                        const v1 = latLngToVector3(lat1, lng1, radius);
                        const v2 = latLngToVector3(lat2, lng2, radius);

                        positions.push(...v1, ...v2);
                    }
                });
            };

            if (type === "Polygon") {
                processPolygon(coords);
            } else if (type === "MultiPolygon") {
                coords.forEach(processPolygon);
            }
        });

        const g = new THREE.BufferGeometry();
        g.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(positions, 3)
        );
        return g;
    }, [geo]);

    return (
        <lineSegments geometry={geometry}>
            <lineBasicMaterial
                color="white"
                transparent
                opacity={0.35}
                depthWrite={false}
            />
        </lineSegments>
    );
}

function LandDotGlobe() {
    const ref = useRef<THREE.Points>(null);
    const geo = useLoader(THREE.FileLoader, "/data/world.geo.json");

    const positions = useMemo(() => {
        const geojson = JSON.parse(geo as string);

        // Arrays to hold dot positions
        const dots: number[] = [];
        const radius = 1;
        const MAX_DOTS = 16000;

        let attempts = 0;

        // Generate dots until we reach MAX_DOTS or hit safe iteration limit
        while (dots.length < MAX_DOTS * 3 && attempts < MAX_DOTS * 20) {
            attempts++;

            // Random lat/lng
            const lat = Math.random() * 180 - 90;
            const lng = Math.random() * 360 - 180;

            // 🔑 LAND CHECK using D3
            // Check if point is inside any feature in the GeoJSON
            const isOnLand = geojson.features.some((f: any) =>
                d3.geoContains(f, [lng, lat])
            );

            if (isOnLand) {
                dots.push(...latLngToVector3(lat, lng, radius));
            }
        }

        return new Float32Array(dots);
    }, [geo]);

    useFrame((_, d) => {
        if (ref.current) ref.current.rotation.y += d * 0.12;
    });

    return (
        <Points ref={ref} positions={positions} stride={3}>
            <PointMaterial
                color="white"
                size={0.0035}
                sizeAttenuation
                transparent
                opacity={0.9}
                depthWrite={false}
            />
        </Points>
    );
}

export default function FinanceGlobe() {
    return (
        <div className="fixed inset-0 z-0 bg-black">
            <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
                {/* No strong lights needed for Basic/Point materials */}
                <ambientLight intensity={0.3} />

                <Suspense fallback={null}>
                    <CountryBorders />
                    <LandDotGlobe />
                </Suspense>
            </Canvas>
        </div>
    );
}
