const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// Set local path if binary exists in the root folder (helpful if system-wide installation fails)
const localYtdlpPath = path.join(__dirname, '../yt-dlp.exe');
let ytdlpCmd = 'yt-dlp';

if (fs.existsSync(localYtdlpPath)) {
  ytdlpCmd = `"${localYtdlpPath}"`;
  console.log(`[${new Date().toISOString()}] [YouTube] Auto-configured local yt-dlp: ${localYtdlpPath}`);
}

/**
 * Helper to execute terminal commands in an async wrapper.
 */
function runCommand(command) {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject(error);
        return;
      }
      resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
    });
  }
  );
}

class YouTubeDownloader {
  /**
   * Search and download the first matching audio from YouTube using yt-dlp.
   * @param {string} query - The song name search query
   * @param {string} outputDir - Directory where downloaded files should be stored
   * @returns {Promise<{ filePath: string, title: string, id: string }>} - Metadata of downloaded audio file
   */
  static async downloadSong(query, outputDir) {
    console.log(`[${new Date().toISOString()}] [YouTube] Initiating search for query: "${query}"`);

    // Ensure output directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Define unique temp file path structure using yt-dlp templates
    // We download as bestaudio and let yt-dlp extract it to a temporary audio file (e.g. mp3/m4a)
    const outputTemplate = path.join(outputDir, '%(id)s.%(ext)s');
    
    // We use --print to capture the final filename and video details
    // yt-dlp arguments:
    // - "ytsearch1:<query>" search for 1 video
    // - -x (extract audio)
    // - --audio-format mp3 (extract to mp3 as intermediate format)
    // - --no-playlist (only single video)
    // - --print filename (to know exactly where it was saved)
    // - --print title (to get the song name)
    // - --print id (to get video id)
    // Note: We use double quotes for arguments to avoid shell escaping issues on Windows/Linux.
    // If local ffmpeg exists, pass it to yt-dlp to allow audio extraction
    const localFfmpegPath = path.join(__dirname, '../ffmpeg.exe');
    const localFfmpegDir = path.join(__dirname, '..');
    let ffmpegOpt = '';
    if (fs.existsSync(localFfmpegPath)) {
      ffmpegOpt = `--ffmpeg-location "${localFfmpegDir}"`;
    }

    const escapedQuery = query.replace(/"/g, '\\"');
    const command = `${ytdlpCmd} "ytsearch1:${escapedQuery}" -x --audio-format mp3 --no-playlist -o "${outputTemplate}" --print "filename" --print "title" --print "id" ${ffmpegOpt} --no-simulate`;

    console.log(`[${new Date().toISOString()}] [YouTube] Executing command: ${command}`);

    try {
      const { stdout, stderr } = await runCommand(command);
      
      console.log(`[${new Date().toISOString()}] [YouTube] Command stdout:\n${stdout}`);
      if (stderr) {
        console.warn(`[${new Date().toISOString()}] [YouTube] Command stderr:\n${stderr}`);
      }

      // Parse output lines
      const lines = stdout.split('\n').map(l => l.trim()).filter(Boolean);
      
      if (lines.length < 3) {
        throw new Error(`Failed to parse yt-dlp output. Raw output: ${stdout}`);
      }

      const filePath = lines[0];
      const title = lines[1];
      const id = lines[2];

      // Double-check file exists
      if (!fs.existsSync(filePath)) {
        // Sometimes yt-dlp appends .mp3 instead of the template ext, search matching file in directory
        const expectedFile = path.join(outputDir, `${id}.mp3`);
        if (fs.existsSync(expectedFile)) {
          return { filePath: expectedFile, title, id };
        }
        throw new Error(`Downloaded file not found at expected path: ${filePath}. (If FFmpeg is missing, yt-dlp cannot extract to mp3)`);
      }

      console.log(`[${new Date().toISOString()}] [YouTube] Successfully downloaded: "${title}" (ID: ${id}) -> ${filePath}`);
      return { filePath, title, id };

    } catch (err) {
      // If runCommand threw an error, check if it contains stdout/stderr
      if (err.stdout) console.log(`[${new Date().toISOString()}] [YouTube] Error stdout:\n${err.stdout}`);
      if (err.stderr) console.error(`[${new Date().toISOString()}] [YouTube] Error stderr:\n${err.stderr}`);

      console.error(`[${new Date().toISOString()}] [YouTube] Error downloading song "${query}":`, err.message);
      
      // Attempt fallback: check if the executable itself was not found
      if ((err.message.includes('not found') || err.message.includes('is not recognized')) && !err.message.includes('Downloaded file not found')) {
        throw new Error('yt-dlp is not installed or configured correctly in the project root.');
      }
      
      throw err;
    }
  }
}

module.exports = YouTubeDownloader;
