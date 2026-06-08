import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { GeistPixelSquare } from 'geist/font/pixel';
import './globals.css';
import { AppShell } from '@/components/app-shell';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Sikto',
  description: 'Video automation and microlearning platform.',
};

const fontVars = `${geistSans.variable} ${geistMono.variable} ${GeistPixelSquare.variable}`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${fontVars} h-full antialiased`}>
      <body className="min-h-full bg-background font-sans text-foreground">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
