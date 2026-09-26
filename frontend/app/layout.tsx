import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "leaflet/dist/leaflet.css";

import Navbar from "@/components/Navbar";

import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
  style: ["normal", "italic"],
  variable: "--font-poppins",
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
    <html lang="en" className={poppins.variable}>
      <body>
        <div className="flex min-h-screen flex-col">
          <Navbar />
          <div className="flex-1 min-h-0">{children}</div>
        </div>
      </body>
    </html>
  );
}
