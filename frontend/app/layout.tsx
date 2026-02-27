import type { Metadata } from "next";
import { Geist, Geist_Mono, Zalando_Sans_SemiExpanded } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const zalandoSansSemiExpanded = Zalando_Sans_SemiExpanded({
  variable: "--font-brand",
  subsets: ["latin"],
  weight: "700",
});

export const metadata: Metadata = {
  title: "Seagull",
  description: "Seagull — Research Intelligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${zalandoSansSemiExpanded.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
