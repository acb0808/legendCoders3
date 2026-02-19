'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from './auth-provider';
import { LayoutDashboard, Trophy, BookOpen, LogOut, User, Menu } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const navItems = [
    { name: '대시보드', href: '/dashboard', icon: LayoutDashboard },
    { name: '오늘의 문제', href: '/problems/today', icon: BookOpen },
    { name: '랭킹', href: '/ranking', icon: Trophy },
  ];

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/dashboard" className="flex-shrink-0 flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
                L
              </div>
              <span className="text-xl font-bold text-gray-900 tracking-tight hidden sm:block">
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
                        ? "bg-blue-50 text-blue-700" 
                        : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
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
            <div className="hidden md:flex flex-col items-end mr-2">
              <span className="text-sm font-bold text-gray-900">{user.nickname}</span>
              <span className="text-xs text-gray-500 font-mono">{user.baekjoon_id}</span>
            </div>
            
            <button
              onClick={logout}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
              title="로그아웃"
            >
              <LogOut size={20} />
            </button>
            
            <div className="sm:hidden flex items-center">
              <button className="p-2 text-gray-400 hover:bg-gray-100 rounded-xl">
                <Menu size={24} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
