import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import { ThemeProvider } from "@/components/ThemeProvider";
import { openGraphShared } from "./shared-metadata";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: {
    template: "%s | Pantheon Code Plagiarism Detector",
    default: "Pantheon Code Plagiarism Detector"
  },
  description: "Web-based plagiarism detection system for academic programming assignments.",
  openGraph: {
    ...openGraphShared,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <Navbar />
          {children}
          <Footer />
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
