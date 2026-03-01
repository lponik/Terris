"use client";

import { useCallback, useMemo } from "react";
import Particles from "react-tsparticles";
import { loadSlim } from "tsparticles-slim";
import type { Engine, ISourceOptions } from "tsparticles-engine";

export default function StarfieldBackground() {
  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine);
  }, []);

  const options = useMemo<ISourceOptions>(
    () => ({
      fullScreen: { enable: false },
      detectRetina: true,
      background: { color: "transparent" },
      fpsLimit: 50,
      interactivity: {
        events: {
          onClick: { enable: false },
          onHover: { enable: false },
          resize: true,
        },
      },
      particles: {
        color: { value: ["#0f6f43", "#2e965f", "#69c08f"] },
        links: { enable: false },
        move: {
          enable: true,
          speed: 0.34,
          direction: "none",
          outModes: { default: "out" },
          random: true,
          straight: false,
        },
        number: {
          density: { enable: true, area: 900 },
          value: 160,
        },
        opacity: {
          value: { min: 0.2, max: 0.75 },
          animation: { enable: true, speed: 0.18, sync: false },
        },
        shape: { type: "circle" },
        size: {
          value: { min: 0.6, max: 2.4 },
          animation: { enable: true, speed: 0.22, sync: false },
        },
        twinkle: {
          particles: {
            enable: true,
            frequency: 0.03,
            opacity: 1,
            color: { value: "#69c08f" },
          },
        },
      },
    }),
    [],
  );

  return (
    <Particles
      id="terris-stars"
      init={particlesInit}
      options={options}
      className="pointer-events-none absolute inset-0 z-0"
    />
  );
}
