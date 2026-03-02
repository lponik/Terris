"use client";

import type { CSSProperties, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

interface ScrollRevealProps {
  children: ReactNode;
  className?: string;
  delayMs?: number;
  threshold?: number;
  rootMargin?: string;
  once?: boolean;
}

export default function ScrollReveal({
  children,
  className = "",
  delayMs = 0,
  threshold = 0.2,
  rootMargin = "0px 0px -10% 0px",
  once = true,
}: ScrollRevealProps) {
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    if (typeof window !== "undefined" && !("IntersectionObserver" in window)) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (!entry) {
          return;
        }

        if (entry.isIntersecting) {
          setIsVisible(true);
          if (once) {
            observer.unobserve(entry.target);
          }
          return;
        }

        if (!once) {
          setIsVisible(false);
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [once, rootMargin, threshold]);

  const style = {
    "--reveal-delay": `${delayMs}ms`,
  } as CSSProperties;

  const resolvedClassName = `scroll-reveal ${isVisible ? "scroll-reveal--visible" : ""} ${className}`.trim();

  return (
    <div ref={containerRef} className={resolvedClassName} style={style}>
      {children}
    </div>
  );
}
