import { NextResponse } from 'next/server';

// Internal backend URL (not exposed externally)
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend-service:8080/api';

export async function GET() {
	try {
		const response = await fetch(`${BACKEND_URL}/research-sessions`);
		const data = await response.json();
		return NextResponse.json(data);
	} catch (error) {
		console.error('Error fetching research sessions:', error);
		return NextResponse.json({ error: 'Failed to fetch research sessions' }, { status: 500 });
	}
}
