import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { GeistPixelSquare } from 'geist/font/pixel';
import './globals.css';
import { AuthProvider } from '@/components/auth/auth-provider';

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
      <head>
        {/* Loaded by real family name ("Caveat"/"Geist") so the scene canvas —
            which references families literally and measures them on a canvas —
            resolves the same fonts the Remotion MP4 does. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Geist:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full bg-background font-sans text-foreground">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
