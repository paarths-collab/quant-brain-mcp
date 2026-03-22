'use client';
import React, { useEffect, useRef, useMemo, forwardRef, useImperativeHandle } from 'react';
import * as THREE from 'three';

const VERT = `
precision highp float;
attribute vec3 position;
attribute vec2 uv;
uniform mat4 modelViewMatrix;
uniform mat4 projectionMatrix;
varying vec2 vUv;
void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FRAG = `
precision highp float;
uniform vec3 iResolution;
uniform float iTime;
uniform float uFlowTime;
uniform float uFogTime;
uniform float uWispDensity;
uniform float uMouseTilt;
uniform float uBeamXFrac;
uniform float uBeamYFrac;
uniform float uFlowSpeed;
uniform float uHLenFactor;
uniform float uVLenFactor;
uniform vec3 uColor;
uniform float uFogIntensity;
uniform float uFogScale;
uniform float uWispSpeed;
uniform float uWispIntensity;
uniform float uFlowStrength;
uniform float uDecay;
uniform float uFalloffStart;
uniform float uFogFallSpeed;
uniform float uFade;
varying vec2 vUv;

#define PI 3.14159265
#define TWO_PI 6.28318530
#define FLARE_HEIGHT 0.1
#define FLARE_EXP 0.4
#define R_H 0.5
#define R_V 0.5
#define W_AA 0.005
#define EPS 0.000001
#define TAP_RADIUS 1
#define DT_LOCAL 0.02
#define FOG_OCTAVES 5

float vnoise(vec2 p){
    vec2 i=floor(p),f=fract(p);
    float a=sin(dot(i,vec2(12.9898,78.233))),b=sin(dot(i+vec2(1,0),vec2(12.9898,78.233))),
          c=sin(dot(i+vec2(0,1),vec2(12.9898,78.233))),d=sin(dot(i+vec2(1,1),vec2(12.9898,78.233)));
    vec2 u=f*f*(3.0-2.0*f);
    return mix(a,b,u.x)+(c-a)*u.y*(1.0-u.x)+(d-b)*u.x*u.y;
}
float fbm2(vec2 p){
    float v=0.0,amp=0.6; mat2 m=mat2(0.86,0.5,-0.5,0.86);
    for(int i=0;i<FOG_OCTAVES;++i){v+=amp*vnoise(p); p=m*p*2.03+17.1; amp*=0.52;}
    return v;
}
float rGate(float x,float l){float a=smoothstep(0.0,W_AA,x),b=1.0-smoothstep(l,l+W_AA,x);return max(0.0,a*b);}
float flareY(float y){float t=clamp(1.0-(clamp(y,0.0,FLARE_HEIGHT)/max(FLARE_HEIGHT,EPS)),0.0,1.0);return pow(t,FLARE_EXP);}

float tauWf(float t,float tm,float tmx){
    float d=tmx-tm; if(d<=EPS)return 0.0;
    float u=clamp((t-tm)/d,0.0,1.0); return smoothstep(0.0,0.1,u)*smoothstep(1.0,0.9,u);
}

void main() {
    float pr=iResolution.z; vec2 frag=vUv*iResolution.xy;
    vec2 C=0.5*iResolution.xy,sc=vec2(1.0/min(iResolution.x,iResolution.y));
    vec2 uv=(frag-C)*sc,off=vec2(uBeamXFrac*iResolution.x*sc.x,uBeamYFrac*iResolution.y*sc.y);
    vec2 uvc = uv - off;
    float a=0.0,b=0.0;
    float basePhase=1.5*PI+uDecay*.5; float tauMin=basePhase-uDecay; float tauMax=basePhase;
    float cx=clamp(uvc.x/(R_H*uHLenFactor),-1.0,1.0),tH=clamp(TWO_PI-acos(cx),tauMin,tauMax);
    for(int k=-TAP_RADIUS;k<=TAP_RADIUS;++k){
        float tu=tH+float(k)*DT_LOCAL,wt=tauWf(tu,tauMin,tauMax); if(wt<=0.0) continue;
        float spd=max(abs(sin(tu)),0.02),u=clamp((basePhase-tu)/max(uDecay,EPS),0.0,1.0),env=pow(1.0-abs(u*2.0-1.0),0.8);
        float cap=smoothstep(uFalloffStart,1.0,env); env*=cap;
        float yL=sin(tu)*R_V*uVLenFactor,yL_next=sin(tu+DT_LOCAL)*R_V*uVLenFactor;
        float sL=abs(yL_next-yL)/DT_LOCAL;
        float n1=vnoise(vec2(tu*1.5,uFlowTime*uFlowSpeed*spd)),n2=vnoise(vec2(tu*2.0+1.2,uFlowTime*uFlowSpeed*0.8*spd));
        float nf=mix(n1,n2,0.5);
        float yO=uvc.y-yL,g=rGate(abs(yO),uFlowStrength*nf*env);
        a+=g*wt; b+=yO*g*wt;
    }
    if(a>EPS) b/=a;
    float env_final=pow(1.0-abs(clamp((basePhase-tH)/max(uDecay,EPS),0.0,1.0)*2.0-1.0),0.8);
    float br=a*rGate(abs(uvc.y-b),0.01)*env_final;
    float fy=flareY(abs(uvc.y-b));
    vec3 col=uColor*br+uColor*fy*0.12*env_final;

    vec2 pW=uvc*2.0; pW.y-=b; pW.x+=uWispSpeed*uFlowTime;
    float wn=vnoise(pW*uWispDensity);
    col+=uColor*wn*uWispIntensity*env_final*a;

    float fog=fbm2(uv*uFogScale+vec2(uFogFallSpeed*uFogTime,0.0));
    col+=uColor*fog*uFogIntensity;

    gl_FragColor = vec4(col*uFade,1.0);
}
`;

export interface LaserFlowProps {
  className?: string;
  style?: React.CSSProperties;
  wispDensity?: number;
  dpr?: number;
  mouseSmoothTime?: number;
  mouseTiltStrength?: number;
  horizontalBeamOffset?: number;
  verticalBeamOffset?: number;
  flowSpeed?: number;
  verticalSizing?: number;
  horizontalSizing?: number;
  fogIntensity?: number;
  fogScale?: number;
  wispSpeed?: number;
  wispIntensity?: number;
  flowStrength?: number;
  decay?: number;
  falloffStart?: number;
  fogFallSpeed?: number;
  color?: string;
}

export interface LaserFlowRef {
  canvas: HTMLCanvasElement | null;
}

const LaserFlow = forwardRef<LaserFlowRef, LaserFlowProps>((props, ref) => {
  const {
    className = "",
    style = {},
    wispDensity = 4.5,
    dpr = 0,
    mouseSmoothTime = 0.1,
    mouseTiltStrength = 0.05,
    horizontalBeamOffset = 0,
    verticalBeamOffset = 0,
    flowSpeed = 1.0,
    verticalSizing = 1.0,
    horizontalSizing = 1.0,
    fogIntensity = 0.02,
    fogScale = 2.5,
    wispSpeed = 0.2,
    wispIntensity = 0.05,
    flowStrength = 0.3,
    decay = 2.0,
    falloffStart = 0.1,
    fogFallSpeed = 0.03,
    color = "#4f46e5"
  } = props;

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const uniformsRef = useRef<any>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const rafRef = useRef<number>(0);
  const lastDprRef = useRef<number>(0);
  const rectRef = useRef<DOMRect | null>(null);
  const pausedRef = useRef<boolean>(false);
  const inViewRef = useRef<boolean>(false);
  const hasFadedRef = useRef<boolean>(false);

  const fpsSamplesRef = useRef<number[]>([]);
  const lastFpsCheckRef = useRef<number>(0);
  const currentDprRef = useRef<number>(1);
  const baseDprRef = useRef<number>(1);

  const mouseTarget = useRef({ x: 0, y: 0 });
  const mouseSmooth = useRef({ x: 0, y: 0 });

  useImperativeHandle(ref, () => ({
    canvas: canvasRef.current,
  }));

  const hexToRGB = (hex: string) => {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;
    return new THREE.Vector3(r, g, b);
  };

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true });
    rendererRef.current = renderer;
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.Camera();
    const geometry = new THREE.PlaneGeometry(2, 2);

    const uniforms = {
      iResolution: { value: new THREE.Vector3() },
      iTime: { value: 0 },
      uFlowTime: { value: 0 },
      uFogTime: { value: 0 },
      uWispDensity: { value: wispDensity },
      uMouseTilt: { value: 0 },
      uBeamXFrac: { value: horizontalBeamOffset },
      uBeamYFrac: { value: verticalBeamOffset },
      uFlowSpeed: { value: flowSpeed },
      uHLenFactor: { value: horizontalSizing },
      uVLenFactor: { value: verticalSizing },
      uFogIntensity: { value: fogIntensity },
      uFogScale: { value: fogScale },
      uWispSpeed: { value: wispSpeed },
      uWispIntensity: { value: wispIntensity },
      uFlowStrength: { value: flowStrength },
      uDecay: { value: decay },
      uFalloffStart: { value: falloffStart },
      uFogFallSpeed: { value: fogFallSpeed },
      uColor: { value: hexToRGB(color) },
      uFade: { value: 0 }
    };
    uniformsRef.current = uniforms;

    const material = new THREE.RawShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms,
      transparent: true,
      depthWrite: false,
      depthTest: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    let resizeRaf: number;
    const lastSize = { width: 0, height: 0, dpr: 0 };

    const setSizeNow = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      const pr = currentDprRef.current;
      if (w === lastSize.width && h === lastSize.height && pr === lastSize.dpr) return;

      lastSize.width = w;
      lastSize.height = h;
      lastSize.dpr = pr;

      renderer.setPixelRatio(pr);
      renderer.setSize(w, h, false);
      uniforms.iResolution.value.set(w * pr, h * pr, pr);
      rectRef.current = canvas.getBoundingClientRect();
    };

    const scheduleResize = () => {
      cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(setSizeNow);
    };

    const ro = new ResizeObserver(scheduleResize);
    ro.observe(container);

    const onVis = (entries: IntersectionObserverEntry[]) => {
      inViewRef.current = entries[0].isIntersecting;
    };
    const io = new IntersectionObserver(onVis, { threshold: 0 });
    io.observe(container);

    const onMove = (e: any) => {
      if (!rectRef.current) return;
      const x = ((e.clientX - rectRef.current.left) / rectRef.current.width) * 2 - 1;
      const y = -((e.clientY - rectRef.current.top) / rectRef.current.height) * 2 + 1;
      mouseTarget.current.x = x;
      mouseTarget.current.y = y;
    };

    const onTouch = (e: TouchEvent) => {
      if (e.touches.length > 0) onMove(e.touches[0]);
    };

    const onLeave = () => {
      mouseTarget.current.x = 0;
      mouseTarget.current.y = 0;
    };

    const onCtxLost = (e: Event) => {
      e.preventDefault();
      pausedRef.current = true;
    };
    const onCtxRestored = () => {
      pausedRef.current = false;
      scheduleResize();
    };

    canvas.addEventListener('mousemove', onMove);
    canvas.addEventListener('touchstart', onTouch);
    canvas.addEventListener('touchmove', onTouch);
    canvas.addEventListener('mouseleave', onLeave);
    canvas.addEventListener('webglcontextlost', onCtxLost);
    canvas.addEventListener('webglcontextrestored', onCtxRestored);

    const clock = new THREE.Clock();
    let prevTime = 0;
    const dprFloor = 0.5;
    const lowerThresh = 40;
    const upperThresh = 54;
    const dprChangeCooldown = 5000;
    let lastDprChange = 0;
    let raf: number;

    const adjustDprIfNeeded = (now: number) => {
      const elapsed = now - lastFpsCheckRef.current;
      if (elapsed < 750) return;

      const samples = fpsSamplesRef.current;
      if (samples.length === 0) {
        lastFpsCheckRef.current = now;
        return;
      }
      const avgFps = samples.reduce((a, b) => a + b, 0) / samples.length;

      let next = currentDprRef.current;
      const base = baseDprRef.current;

      if (avgFps < lowerThresh) {
        next = Math.max(dprFloor, currentDprRef.current * 0.85);
      } else if (avgFps > upperThresh && currentDprRef.current < base) {
        next = Math.min(base, currentDprRef.current * 1.1);
      }

      if (Math.abs(next - currentDprRef.current) > 0.01 && now - lastDprChange > dprChangeCooldown) {
        currentDprRef.current = next;
        lastDprChange = now;
        setSizeNow();
      }

      fpsSamplesRef.current = [];
      lastFpsCheckRef.current = now;
    };

    const animate = () => {
      raf = requestAnimationFrame(animate);
      if (pausedRef.current || !inViewRef.current) return;

      const t = clock.getElapsedTime();
      const dt = Math.max(0, t - prevTime);
      prevTime = t;

      const dtMs = dt * 1000;
      const instFps = 1000 / Math.max(1, dtMs);
      fpsSamplesRef.current.push(instFps);

      uniforms.iTime.value = t;
      const cdt = Math.min(0.033, Math.max(0.001, dt));
      uniforms.uFlowTime.value += cdt;
      uniforms.uFogTime.value += cdt;

      if (!hasFadedRef.current) {
        uniforms.uFade.value += dt * 1.5;
        if (uniforms.uFade.value >= 1) {
          uniforms.uFade.value = 1;
          hasFadedRef.current = true;
        }
      }

      mouseSmooth.current.x += (mouseTarget.current.x - mouseSmooth.current.x) * 0.1;
      mouseSmooth.current.y += (mouseTarget.current.y - mouseSmooth.current.y) * 0.1;
      uniforms.uMouseTilt.value = mouseSmooth.current.x * mouseTiltStrength;

      renderer.render(scene, camera);
      adjustDprIfNeeded(performance.now());
    };

    raf = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(resizeRaf);
      ro.disconnect();
      io.disconnect();
      canvas.removeEventListener('mousemove', onMove);
      canvas.removeEventListener('touchstart', onTouch);
      canvas.removeEventListener('touchmove', onTouch);
      canvas.removeEventListener('mouseleave', onLeave);
      canvas.removeEventListener('webglcontextlost', onCtxLost);
      canvas.removeEventListener('webglcontextrestored', onCtxRestored);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  useEffect(() => {
    if (!uniformsRef.current) return;
    const u = uniformsRef.current;
    u.uWispDensity.value = wispDensity;
    u.uBeamXFrac.value = horizontalBeamOffset;
    u.uBeamYFrac.value = verticalBeamOffset;
    u.uFlowSpeed.value = flowSpeed;
    u.uHLenFactor.value = horizontalSizing;
    u.uVLenFactor.value = verticalSizing;
    u.uFogIntensity.value = fogIntensity;
    u.uFogScale.value = fogScale;
    u.uWispSpeed.value = wispSpeed;
    u.uWispIntensity.value = wispIntensity;
    u.uFlowStrength.value = flowStrength;
    u.uDecay.value = decay;
    u.uFalloffStart.value = falloffStart;
    u.uFogFallSpeed.value = fogFallSpeed;
    u.uColor.value = hexToRGB(color);
    
    if (dpr > 0) {
      baseDprRef.current = dpr;
      if (currentDprRef.current > dpr) {
         currentDprRef.current = dpr;
      }
    } else {
      baseDprRef.current = window.devicePixelRatio || 1;
    }
  }, [
    wispDensity,
    horizontalBeamOffset,
    verticalBeamOffset,
    flowSpeed,
    horizontalSizing,
    verticalSizing,
    fogIntensity,
    fogScale,
    wispSpeed,
    wispIntensity,
    flowStrength,
    decay,
    falloffStart,
    fogFallSpeed,
    color,
    dpr
  ]);

  return (
    <div ref={containerRef} className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`} style={{ zIndex: 0, ...style }}>
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  );
});

LaserFlow.displayName = "LaserFlow";

export { LaserFlow };
