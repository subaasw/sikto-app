import type { Metadata } from 'next';
import { Archivo_Black, Bricolage_Grotesque, Caveat, Geist, Geist_Mono } from 'next/font/google';
import { GeistPixelSquare } from 'geist/font/pixel';
import { ThemeProvider } from 'next-themes';
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

const archivoBlack = Archivo_Black({
  variable: '--font-archivo-black',
  weight: '400',
  subsets: ['latin'],
});

const bricolageGrotesque = Bricolage_Grotesque({
  variable: '--font-bricolage-grotesque',
  weight: ['700', '800'],
  subsets: ['latin'],
});

const caveat = Caveat({
  variable: '--font-caveat',
  weight: ['500', '600', '700'],
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Sikto',
  description: 'Video automation and microlearning platform.',
};

const fontVars = [
  geistSans.variable,
  geistMono.variable,
  GeistPixelSquare.variable,
  archivoBlack.variable,
  bricolageGrotesque.variable,
  caveat.variable,
].join(' ');

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${fontVars} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full bg-background font-sans text-foreground" suppressHydrationWarning>
        <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
