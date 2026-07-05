const crypto = require("crypto");

function normalizeGraphBaseUrl(baseUrl) {
  const trimmed = String(baseUrl || "")
    .trim()
    .replace(/\/$/, "");
  if (!trimmed) {
    throw new Error("Instagram Graph base URL is missing.");
  }
  return trimmed;
}

function verifyWebhookSignature(rawBody, signatureHeader, appSecret) {
  if (!appSecret) {
    return true;
  }

  if (!signatureHeader || typeof signatureHeader !== "string") {
    return false;
  }

  const expected = `sha256=${crypto.createHmac("sha256", appSecret).update(rawBody).digest("hex")}`;
  const expectedBuffer = Buffer.from(expected, "utf8");
  const providedBuffer = Buffer.from(signatureHeader, "utf8");

  if (expectedBuffer.length !== providedBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(expectedBuffer, providedBuffer);
}

async function sendTextMessage({
  baseUrl,
  accessToken,
  recipientId,
  text,
  messagingType = "RESPONSE",
}) {
  if (!accessToken) {
    throw new Error("Instagram Graph access token is missing.");
  }

  if (!recipientId) {
    throw new Error("Recipient ID is missing.");
  }

  const graphBaseUrl = normalizeGraphBaseUrl(
    baseUrl || "https://graph.facebook.com/v21.0",
  );
  const endpoint = `${graphBaseUrl}/me/messages?access_token=${encodeURIComponent(accessToken)}`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      recipient: { id: recipientId },
      messaging_type: messagingType,
      message: { text },
    }),
  });

  const responseText = await response.text();
  let payload = null;
  try {
    payload = responseText ? JSON.parse(responseText) : null;
  } catch {
    payload = { raw: responseText };
  }

  if (!response.ok) {
    const details =
      payload?.error?.message || payload?.raw || response.statusText;
    throw new Error(
      `Graph API message send failed (${response.status}): ${details}`,
    );
  }

  return payload;
}

module.exports = {
  sendTextMessage,
  verifyWebhookSignature,
};
