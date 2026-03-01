import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";

import Navbar from "@/components/Navbar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Terris",
  description: "Terris: national environmental exposure proxy mapping",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col">
          <Navbar />
          <div className="flex-1 min-h-0">{children}</div>
        </div>
      </body>
    </html>
  );
}
