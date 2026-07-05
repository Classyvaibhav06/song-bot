require("dotenv").config();

const fs = require("fs");
const http = require("http");
const path = require("path");
const { URL } = require("url");

const RateLimiter = require("./lib/rate-limiter");
const { resolveSong, formatSongReply } = require("./lib/song-resolver");
const {
  sendTextMessage,
  verifyWebhookSignature,
} = require("./lib/instagram-graph");

function readJsonFile(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return {};
  }
}

const configPath = path.join(__dirname, "config.json");
const config = readJsonFile(configPath);

const settings = {
  port: Number(process.env.PORT || config.server?.port || 3000),
  verifyToken:
    process.env.IG_VERIFY_TOKEN ||
    config.webhook?.verifyToken ||
    config.instagram?.verifyToken,
  appSecret:
    process.env.IG_APP_SECRET ||
    config.webhook?.appSecret ||
    config.instagram?.appSecret,
  accessToken:
    process.env.IG_PAGE_ACCESS_TOKEN ||
    config.instagram?.pageAccessToken ||
    config.webhook?.pageAccessToken,
  graphBaseUrl:
    process.env.IG_GRAPH_BASE_URL ||
    config.instagram?.graphBaseUrl ||
    "https://graph.facebook.com/v21.0",
  messagingWindowHours: Number(
    process.env.IG_MESSAGING_WINDOW_HOURS ||
      config.limits?.messagingWindowHours ||
      24,
  ),
  commandsPerHour: Number(
    process.env.IG_COMMANDS_PER_HOUR || config.limits?.commandsPerHour || 30,
  ),
  logFile: path.resolve(
    __dirname,
    config.paths?.logFile || "./logs/interactions.log",
  ),
};

if (!settings.verifyToken) {
  throw new Error(
    "Missing IG_VERIFY_TOKEN. Set it in the environment or config.json.",
  );
}

if (!settings.accessToken) {
  throw new Error(
    "Missing IG_PAGE_ACCESS_TOKEN. Set it in the environment or config.json.",
  );
}

const rateLimiter = new RateLimiter(settings.commandsPerHour);

function ensureLogDirectory() {
  fs.mkdirSync(path.dirname(settings.logFile), { recursive: true });
}

function logInteraction(entry) {
  ensureLogDirectory();
  const line = JSON.stringify({
    timestamp: new Date().toISOString(),
    ...entry,
  });
  fs.appendFileSync(settings.logFile, `${line}\n`, "utf8");
}

function parseBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];

    request.on("data", (chunk) => {
      chunks.push(chunk);
      const size = chunks.reduce((total, part) => total + part.length, 0);
      if (size > 1_000_000) {
        reject(new Error("Request body too large."));
        request.destroy();
      }
    });

    request.on("end", () => {
      const rawBody = Buffer.concat(chunks);
      if (!rawBody.length) {
        resolve({ rawBody, parsed: {} });
        return;
      }

      try {
        resolve({ rawBody, parsed: JSON.parse(rawBody.toString("utf8")) });
      } catch (error) {
        reject(new Error(`Invalid JSON payload: ${error.message}`));
      }
    });

    request.on("error", reject);
  });
}

function isWithinMessagingWindow(timestamp) {
  const eventTimestamp = Number(timestamp);
  if (!Number.isFinite(eventTimestamp)) {
    return true;
  }

  const ageMs = Date.now() - eventTimestamp;
  return ageMs <= settings.messagingWindowHours * 60 * 60 * 1000;
}

function isCommandMessage(text) {
  return typeof text === "string" && text.trim().startsWith("/");
}

function parseCommand(text) {
  const normalized = String(text || "").trim();
  const [command, ...rest] = normalized.split(/\s+/);
  return {
    command: command.toLowerCase(),
    argument: rest.join(" ").trim(),
  };
}

async function reply(recipientId, text) {
  return sendTextMessage({
    baseUrl: settings.graphBaseUrl,
    accessToken: settings.accessToken,
    recipientId,
    text,
    messagingType: "RESPONSE",
  });
}

async function handlePlayCommand(event, commandText) {
  const senderId = event.sender?.id;
  const text = event.message?.text || "";
  const { argument } = parseCommand(commandText);

  if (!argument) {
    const usage =
      "Send /play followed by a song title, for example: /play midnight city.";
    await reply(senderId, usage);
    logInteraction({
      level: "info",
      senderId,
      command: "/play",
      status: "missing_query",
    });
    return;
  }

  if (!rateLimiter.isAllowed(senderId)) {
    const message =
      "You have hit the hourly command limit. Please try again later.";
    await reply(senderId, message);
    logInteraction({
      level: "warn",
      senderId,
      command: "/play",
      status: "rate_limited",
      text,
    });
    return;
  }

  logInteraction({
    level: "info",
    senderId,
    command: "/play",
    status: "searching",
    query: argument,
  });

  const song = await resolveSong(argument);
  const responseText = formatSongReply(song, argument);

  await reply(senderId, responseText);
  logInteraction({
    level: song ? "info" : "warn",
    senderId,
    command: "/play",
    status: song ? "sent" : "unknown_song",
    query: argument,
    source: song?.source || null,
    trackUrl: song?.trackUrl || null,
  });
}

async function handleMessageEvent(event) {
  const message = event.message || {};
  const senderId = event.sender?.id;
  const recipientId = event.recipient?.id;
  const text = typeof message.text === "string" ? message.text.trim() : "";
  const timestamp = Number(event.timestamp || Date.now());

  if (!senderId || message.is_echo) {
    return;
  }

  if (!isWithinMessagingWindow(timestamp)) {
    logInteraction({
      level: "warn",
      senderId,
      recipientId,
      status: "ignored_outside_window",
      text,
    });
    return;
  }

  if (!text || !isCommandMessage(text)) {
    logInteraction({
      level: "info",
      senderId,
      recipientId,
      status: "ignored_non_command",
      text,
    });
    return;
  }

  const { command, argument } = parseCommand(text);

  try {
    if (command === "/play") {
      await handlePlayCommand(event, argument ? `/play ${argument}` : "/play");
      return;
    }

    if (command === "/help") {
      const helpText = [
        "Commands:",
        "/play [song name] - find a track link or preview",
        "/help - show this message",
      ].join("\n");

      await reply(senderId, helpText);
      logInteraction({
        level: "info",
        senderId,
        command: "/help",
        status: "sent",
      });
      return;
    }

    await reply(senderId, "Unknown command. Try /help for usage.");
    logInteraction({
      level: "info",
      senderId,
      command,
      status: "unknown_command",
      text,
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logInteraction({
      level: "error",
      senderId,
      recipientId,
      command,
      status: "failed",
      error: errorMessage,
      text,
    });

    try {
      await reply(
        senderId,
        "Sorry, I could not complete that request right now.",
      );
    } catch (replyError) {
      logInteraction({
        level: "error",
        senderId,
        command,
        status: "reply_failed",
        error:
          replyError instanceof Error ? replyError.message : String(replyError),
      });
    }
  }
}

async function handleWebhookPost(request, response, rawBody) {
  const signature = request.headers["x-hub-signature-256"];

  if (!verifyWebhookSignature(rawBody, signature, settings.appSecret)) {
    response.writeHead(403, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: "Invalid webhook signature." }));
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawBody.toString("utf8"));
  } catch (error) {
    response.writeHead(400, { "Content-Type": "application/json" });
    response.end(
      JSON.stringify({ error: `Invalid JSON payload: ${error.message}` }),
    );
    return;
  }

  const entries = Array.isArray(payload.entry) ? payload.entry : [];

  for (const entry of entries) {
    const messagingEvents = Array.isArray(entry.messaging)
      ? entry.messaging
      : [];
    for (const event of messagingEvents) {
      await handleMessageEvent(event);
    }
  }

  response.writeHead(200, { "Content-Type": "application/json" });
  response.end(JSON.stringify({ status: "ok" }));
}

function handleWebhookGet(request, response) {
  const url = new URL(request.url, `http://${request.headers.host}`);
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = url.searchParams.get("hub.challenge");

  if (mode === "subscribe" && token === settings.verifyToken) {
    response.writeHead(200, { "Content-Type": "text/plain" });
    response.end(challenge || "");
    return;
  }

  response.writeHead(403, { "Content-Type": "text/plain" });
  response.end("Verification failed.");
}

const server = http.createServer(async (request, response) => {
  try {
    if (request.url && request.url.startsWith("/health")) {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ status: "ok" }));
      return;
    }

    if (
      request.method === "GET" &&
      request.url &&
      request.url.startsWith("/webhook")
    ) {
      handleWebhookGet(request, response);
      return;
    }

    if (
      request.method === "POST" &&
      request.url &&
      request.url.startsWith("/webhook")
    ) {
      const { rawBody } = await parseBody(request);
      await handleWebhookPost(request, response, rawBody);
      return;
    }

    response.writeHead(404, { "Content-Type": "text/plain" });
    response.end("Not found.");
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logInteraction({
      level: "error",
      status: "server_error",
      error: errorMessage,
    });
    response.writeHead(500, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: "Internal server error." }));
  }
});

server.listen(settings.port, () => {
  console.log(
    `[${new Date().toISOString()}] Instagram Graph bot listening on port ${settings.port}`,
  );
  console.log(`[${new Date().toISOString()}] Webhook endpoint: /webhook`);
});
