import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers/Providers";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TerraTrain — KI-Coaching für Ausdauersport",
  description:
    "Verbinde deine Intervals.icu-Daten mit GPX-Streckenanalyse und einem KI-Coach. Strukturierte Workouts über fünf Sportarten – direkt in Intervals.icu.",
  openGraph: {
    title: "TerraTrain — KI-Coaching für Ausdauersport",
    description:
      "KI-geplante, terrain-abgestimmte Workouts über fünf Sportarten, direkt in Intervals.icu.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-bg text-text`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
