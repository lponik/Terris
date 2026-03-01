"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/map", label: "Map" },
  { href: "/learn", label: "Learn" },
  { href: "/about", label: "About" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-[900] border-b border-border bg-panel/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1750px] items-center justify-between px-4 md:h-20 md:px-5">
        <Link
          href="/"
          className="terris-wordmark inline-flex items-center text-2xl font-semibold text-ink transition duration-200 transform-gpu hover:scale-110 hover:text-accent md:text-3xl"
        >
          Terris
        </Link>
        <nav className="flex items-center gap-2 md:gap-3">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`inline-flex items-center rounded-md px-3 py-1.5 text-base font-semibold transition duration-200 transform-gpu hover:scale-110 hover:text-accent md:px-4 md:py-2 md:text-xl ${
                  isActive
                    ? "border border-accent/40 bg-accent/15 text-ink"
                    : "text-muted hover:bg-panelSoft/70"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
