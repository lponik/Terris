import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import "leaflet/dist/leaflet.css";

import Navbar from "@/components/Navbar";

import "./globals.css";

const openSans = Open_Sans({
  subsets: ["latin"],
  variable: "--font-open-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Terris",
  description: "Terris: proximity to mapped Superfund sites and landfills",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={openSans.variable}>
      <body>
        <div className="flex min-h-screen flex-col">
          <Navbar />
          <div className="flex-1 min-h-0">{children}</div>
        </div>
      </body>
    </html>
  );
}
