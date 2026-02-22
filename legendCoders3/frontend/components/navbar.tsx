'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/components/auth-provider';
import { LayoutDashboard, Trophy, BookOpen, LogOut, User, Menu, Crown, Swords } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import TitleBadge from './title-badge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();

  // Don't show navbar on login/register pages
  if (pathname === '/login' || pathname === '/register') return null;
  
  // While loading, show a neutral skeleton to avoid layout shift
  if (loading) return <div className="h-16 bg-white border-b border-gray-100 sticky top-0 z-50" />;

  const isArena = pathname.startsWith('/arena');

  const navItems = [
    { name: '대시보드', href: '/dashboard', icon: LayoutDashboard },
    { name: '오늘의 문제', href: '/problems/today', icon: BookOpen },
    { name: '경쟁전', href: '/arena', icon: Swords },
    { name: '랭킹', href: '/ranking', icon: Trophy },
  ];

  return (
    <nav className={cn(
      "sticky top-0 z-50 shadow-sm transition-colors duration-300",
      isArena 
        ? "bg-slate-900 border-b border-slate-800 text-white" 
        : "bg-white border-b border-gray-100 text-gray-900"
    )}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href={user ? "/dashboard" : "/"} className="flex-shrink-0 flex items-center gap-2">
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white",
                isArena ? "bg-rose-500" : "bg-blue-600"
              )}>
                L
              </div>
              <span className={cn(
                "text-xl font-bold tracking-tight hidden sm:block",
                isArena ? "text-white" : "text-gray-900"
              )}>
                레전드 코더
              </span>
            </Link>
            
            <div className="hidden sm:ml-10 sm:flex sm:space-x-4">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      "inline-flex items-center px-3 py-2 text-sm font-medium rounded-xl transition-all gap-2",
                      isActive 
                        ? (isArena ? "bg-rose-500/20 text-rose-400" : "bg-blue-50 text-blue-700")
                        : (isArena ? "text-slate-400 hover:bg-slate-800 hover:text-white" : "text-gray-500 hover:bg-gray-50 hover:text-gray-700")
                    )}
                  >
                    <item.icon size={18} />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-4">
            {user ? (
              <>
                <Link 
                  href="/profile" 
                  className="hidden md:flex flex-col items-end mr-2 hover:opacity-70 transition-opacity"
                >
                  <div className="flex items-center gap-1.5">
                    <TitleBadge title={user.equipped_title} size="xs" />
                    {user.is_pro && <Crown size={14} className="text-amber-400 fill-amber-400" />}
                    <span className={cn(
                      "text-sm font-bold",
                      user.is_pro ? "text-amber-500" : (isArena ? "text-white" : "text-gray-900")
                    )}>
                      {user.nickname}
                    </span>
                  </div>
                  <span className={cn(
                    "text-xs font-mono",
                    isArena ? "text-slate-500" : "text-gray-500"
                  )}>{user.baekjoon_id}</span>
                </Link>
                
                <button
                  onClick={logout}
                  className={cn(
                    "p-2 rounded-xl transition-all",
                    isArena ? "text-slate-400 hover:text-rose-500 hover:bg-rose-500/10" : "text-gray-400 hover:text-red-500 hover:bg-red-50"
                  )}
                  title="로그아웃"
                >
                  <LogOut size={20} />
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className={cn(
                  "px-4 py-2 rounded-xl text-sm font-bold transition-all",
                  isArena ? "bg-rose-600 text-white hover:bg-rose-500" : "bg-blue-600 text-white hover:bg-blue-700"
                )}
              >
                Sign In
              </Link>
            )}
            
            <div className="sm:hidden flex items-center">
              <button className={cn(
                "p-2 rounded-xl",
                isArena ? "text-slate-400 hover:bg-slate-800" : "text-gray-400 hover:bg-gray-100"
              )}>
                <Menu size={24} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
