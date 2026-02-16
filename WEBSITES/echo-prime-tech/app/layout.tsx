import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Echo Prime Technologies | Autonomous Intelligence Systems',
  description: 'Enterprise AI infrastructure, autonomous intelligence engines, and next-generation data systems. Built for industries that demand precision.',
  keywords: ['AI', 'autonomous systems', 'intelligence engines', 'enterprise AI', 'data infrastructure'],
  openGraph: {
    title: 'Echo Prime Technologies',
    description: 'Autonomous Intelligence Systems',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
