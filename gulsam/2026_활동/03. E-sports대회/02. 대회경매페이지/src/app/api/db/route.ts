import { NextResponse } from 'next/server';
import { readDb, writeDb, Database } from '@/lib/db';

export async function GET() {
  try {
    const db = await readDb();
    return NextResponse.json(db);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to read database' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body: Database = await request.json();
    await writeDb(body);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to update database' }, { status: 500 });
  }
}
