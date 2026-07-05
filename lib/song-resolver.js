const ITUNES_SEARCH_URL = "https://itunes.apple.com/search";

function normalizeQuery(query) {
  return String(query || "")
    .trim()
    .replace(/\s+/g, " ");
}

function buildSpotifySearchUrl(query) {
  return `https://open.spotify.com/search/${encodeURIComponent(query)}`;
}

async function searchItunes(query) {
  const url = new URL(ITUNES_SEARCH_URL);
  url.searchParams.set("term", query);
  url.searchParams.set("media", "music");
  url.searchParams.set("entity", "song");
  url.searchParams.set("limit", "5");

  const response = await fetch(url, {
    headers: {
      "User-Agent": "song-bot/1.0",
    },
  });

  if (!response.ok) {
    throw new Error(`Song lookup failed (${response.status})`);
  }

  const data = await response.json();
  const [track] = Array.isArray(data.results) ? data.results : [];

  if (!track) {
    return null;
  }

  return {
    title: track.trackName || query,
    artist: track.artistName || "Unknown artist",
    album: track.collectionName || null,
    previewUrl: track.previewUrl || null,
    trackUrl: track.trackViewUrl || buildSpotifySearchUrl(query),
    artworkUrl: track.artworkUrl100 || track.artworkUrl60 || null,
    source: "itunes",
  };
}

async function resolveSong(query) {
  const normalized = normalizeQuery(query);

  if (!normalized) {
    throw new Error("Song query is empty.");
  }

  const result = await searchItunes(normalized);

  if (!result) {
    return null;
  }

  return result;
}

function formatSongReply(song, query) {
  if (!song) {
    return [
      `I could not find a match for "${query}".`,
      "Try a fuller title or artist name.",
    ].join(" ");
  }

  const lines = [`Found: ${song.title} - ${song.artist}`];

  if (song.album) {
    lines.push(`Album: ${song.album}`);
  }

  if (song.previewUrl) {
    lines.push(`Preview: ${song.previewUrl}`);
  }

  lines.push(`Link: ${song.trackUrl}`);
  lines.push(`Source: ${song.source}`);

  return lines.join("\n");
}

module.exports = {
  buildSpotifySearchUrl,
  formatSongReply,
  resolveSong,
};
