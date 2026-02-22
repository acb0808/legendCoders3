'use client';

import Link from 'next/link';
import { ArrowRight, Code2, Trophy, Users, Flame } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="bg-white">
      {/* Hero Section */}
      <div className="relative isolate pt-14">
        <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80">
          <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-30 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]"></div>
        </div>
        
        <div className="py-24 sm:py-32 lg:pb-40">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <div className="mb-8 flex justify-center">
                <div className="relative rounded-full px-3 py-1 text-sm leading-6 text-gray-600 ring-1 ring-gray-900/10 hover:ring-gray-900/20">
                  레전드 코더 2기 모집 중{' '}
                  <Link href="/register" className="font-semibold text-blue-600">
                    <span className="absolute inset-0" aria-hidden="true" />
                    더 알아보기 <span aria-hidden="true">&rarr;</span>
                  </Link>
                </div>
              </div>
              <h1 className="text-4xl font-black tracking-tight text-gray-900 sm:text-6xl uppercase italic">
                Every Day, <br />
                <span className="text-blue-600">One Problem.</span>
              </h1>
              <p className="mt-6 text-lg leading-8 text-gray-600 font-medium">
                AI가 엄선하는 오늘의 백준 문제를 매일 하나씩 풀고<br />
                함께 성장하는 개발자들의 커뮤니티, 레전드 코더입니다.
              </p>
              <div className="mt-10 flex items-center justify-center gap-x-6">
                <Link
                  href="/dashboard"
                  className="rounded-2xl bg-blue-600 px-8 py-4 text-sm font-black text-white shadow-xl shadow-blue-100 hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-all uppercase tracking-tighter"
                >
                  시작하기
                </Link>
                <Link href="/login" className="text-sm font-black leading-6 text-gray-900 uppercase tracking-tighter">
                  로그인 <span aria-hidden="true">&rarr;</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Section */}
      <div className="py-24 sm:py-32 bg-gray-50/50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl lg:text-center">
            <h2 className="text-base font-black leading-7 text-blue-600 uppercase tracking-widest italic">Legendary Features</h2>
            <p className="mt-2 text-3xl font-black tracking-tight text-gray-900 sm:text-4xl">
              꾸준함이 실력을 만듭니다
            </p>
          </div>
          <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
            <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
              <div className="flex flex-col bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
                <dt className="flex items-center gap-x-3 text-lg font-black leading-7 text-gray-900 uppercase italic">
                  <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-100">
                    <Code2 size={24} />
                  </div>
                  Daily Problem
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600 font-medium">
                  <p className="flex-auto">매일 12시, AI가 당신의 실력에 맞는 백준 문제를 엄선하여 제공합니다. 백준 제출 ID만으로 간단히 해결 여부를 인증하세요.</p>
                </dd>
              </div>
              <div className="flex flex-col bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
                <dt className="flex items-center gap-x-3 text-lg font-black leading-7 text-gray-900 uppercase italic">
                  <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-orange-600 text-white shadow-lg shadow-orange-100">
                    <Flame size={24} />
                  </div>
                  Streak & Growth
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600 font-medium">
                  <p className="flex-auto">매일 문제를 풀며 스트릭을 유지하세요. 대시보드를 통해 당신의 꾸준함과 성장을 시각적으로 확인할 수 있습니다.</p>
                </dd>
              </div>
              <div className="flex flex-col bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
                <dt className="flex items-center gap-x-3 text-lg font-black leading-7 text-gray-900 uppercase italic">
                  <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-yellow-600 text-white shadow-lg shadow-yellow-100">
                    <Trophy size={24} />
                  </div>
                  Community
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600 font-medium">
                  <p className="flex-auto">해결하지 못한 문제에 대한 힌트를 얻거나, 자신만의 기발한 풀이 방식을 공유하며 동료들과 함께 성장하세요.</p>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
