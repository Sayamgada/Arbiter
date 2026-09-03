import { NextResponse } from "next/server";

export async function GET() {
  const keyId = process.env.RAZORPAY_KEY_ID;

  if (!keyId) {
    return NextResponse.json(
      { error: "RAZORPAY_KEY_ID is not configured" },
      { status: 500 }
    );
  }

  return NextResponse.json({ keyId });
}
