import Link from 'next/link';

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 h-16 border-b border-gold/20 bg-background/80 backdrop-blur-md z-50 flex items-center justify-between px-8">
      <div className="flex items-center gap-8">
        <Link href="/" className="text-xl font-bold gold-gradient-text tracking-widest">
          LOL AUCTION
        </Link>
        <div className="flex gap-6">
          <Link href="/" className="text-sm font-medium hover:text-gold transition-colors">
            AUCTION
          </Link>
          <Link href="/board" className="text-sm font-medium hover:text-gold transition-colors">
            BOARD
          </Link>
        </div>
      </div>
      <div>
        <Link href="/admin" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">
          ADMIN
        </Link>
      </div>
    </nav>
  );
}
