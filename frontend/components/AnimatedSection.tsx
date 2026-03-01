import type { ReactNode } from "react";
import { useMemo, useState } from "react";

interface AnimatedSectionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  isOpen?: boolean;
  onToggle?: () => void;
  contentClassName?: string;
}

export default function AnimatedSection({
  title,
  children,
  defaultOpen = true,
  isOpen,
  onToggle,
  contentClassName,
}: AnimatedSectionProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const resolvedOpen = isOpen ?? internalOpen;

  const contentClasses = useMemo(() => {
    if (!contentClassName) {
      return "overflow-hidden";
    }
    return `overflow-hidden ${contentClassName}`;
  }, [contentClassName]);

  const handleToggle = () => {
    if (onToggle) {
      onToggle();
      return;
    }
    setInternalOpen((current) => !current);
  };

  return (
    <div className="rounded-2xl border border-border bg-panel p-4 transition-all duration-300">
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full cursor-pointer list-none items-center justify-between text-sm font-medium text-muted"
      >
        <span>{title}</span>
        <span className="text-xs text-muted/90">
          {resolvedOpen ? "Hide" : "Show"}
        </span>
      </button>
      <div
        className={`grid overflow-hidden transition-[grid-template-rows,opacity,margin,transform] duration-300 ease-out ${
          resolvedOpen
            ? "mt-3 grid-rows-[1fr] translate-y-0 opacity-100"
            : "mt-0 grid-rows-[0fr] -translate-y-1 opacity-0"
        }`}
      >
        <div className={contentClasses}>{children}</div>
      </div>
    </div>
  );
}
