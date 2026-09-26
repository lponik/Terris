import type { Metadata } from "next";
<<<<<<< Updated upstream
import { Open_Sans } from "next/font/google";
=======
import { Poppins } from "next/font/google";
>>>>>>> Stashed changes
import "leaflet/dist/leaflet.css";

import Navbar from "@/components/Navbar";

import "./globals.css";

<<<<<<< Updated upstream
const openSans = Open_Sans({
  subsets: ["latin"],
  variable: "--font-open-sans",
=======
const poppins = Poppins({
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
  style: ["normal", "italic"],
  variable: "--font-poppins",
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    <html lang="en" className={openSans.variable}>
=======
    <html lang="en" className={poppins.variable}>
>>>>>>> Stashed changes
      <body>
        <div className="flex min-h-screen flex-col">
          <Navbar />
          <div className="flex-1 min-h-0">{children}</div>
        </div>
      </body>
    </html>
  );
}
