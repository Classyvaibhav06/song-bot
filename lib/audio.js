const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');

// Set local paths if binaries exist in the root folder (helpful if system-wide installation fails)
const localFfmpegPath = path.join(__dirname, '../ffmpeg.exe');
const localFfprobePath = path.join(__dirname, '../ffprobe.exe');
let ffmpegCmd = 'ffmpeg';

if (fs.existsSync(localFfmpegPath)) {
  ffmpeg.setFfmpegPath(localFfmpegPath);
  ffmpegCmd = `"${localFfmpegPath}"`;
  console.log(`[${new Date().toISOString()}] [Audio] Auto-configured local FFmpeg: ${localFfmpegPath}`);
}
if (fs.existsSync(localFfprobePath)) {
  ffmpeg.setFfprobePath(localFfprobePath);
  console.log(`[${new Date().toISOString()}] [Audio] Auto-configured local FFprobe: ${localFfprobePath}`);
}

/**
 * Helper to run shell commands as Promise.
 */
function runCommand(command) {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject(error);
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

class AudioProcessor {
  /**
   * Converts any audio file to an Instagram-compliant Voice Note format (.m4a / AAC, Mono, 16000Hz).
   * @param {string} inputPath - Path to the source audio file (e.g., .mp3)
   * @param {string} outputDir - Directory to save the converted file
   * @param {number} maxDurationSeconds - Max duration in seconds (Instagram limits voice notes to 60 or 120s usually)
   * @returns {Promise<{ filePath: string, waveform: number[] }>} - Converted file path and waveform array
   */
  static async convertToVoiceNote(inputPath, outputDir, maxDurationSeconds = 60) {
    console.log(`[${new Date().toISOString()}] [Audio] Converting "${inputPath}" to voice note format (max ${maxDurationSeconds}s)...`);

    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const filename = path.basename(inputPath, path.extname(inputPath)) + '_voice.m4a';
    const outputPath = path.join(outputDir, filename);

    // If already converted, reuse it
    if (fs.existsSync(outputPath)) {
      console.log(`[${new Date().toISOString()}] [Audio] Converted file already exists at: ${outputPath}`);
      const waveform = this.generateWaveform(50); // generate a standard 50-bar waveform
      return { filePath: outputPath, waveform };
    }

    try {
      await new Promise((resolve, reject) => {
        ffmpeg(inputPath)
          .outputOptions([
            '-acodec aac',            // AAC encoding
            '-ac 1',                  // Mono channel
            '-ar 16000',              // 16kHz sample rate (typical for voice notes)
            `-t ${maxDurationSeconds}` // limit duration
          ])
          .save(outputPath)
          .on('end', () => {
            resolve();
          })
          .on('error', (err) => {
            reject(err);
          });
      });
    } catch (err) {
      console.warn(`[${new Date().toISOString()}] [Audio] fluent-ffmpeg failed or config error. Trying raw shell command fallback...`);
      // Fallback: direct command execution
      const command = `${ffmpegCmd} -y -i "${inputPath}" -acodec aac -ac 1 -ar 16000 -t ${maxDurationSeconds} "${outputPath}"`;
      try {
        await runCommand(command);
      } catch (fallbackErr) {
        console.error(`[${new Date().toISOString()}] [Audio] Direct ffmpeg command failed:`, fallbackErr.message);
        throw new Error('ffmpeg is not installed or configured correctly in system PATH.');
      }
    }

    console.log(`[${new Date().toISOString()}] [Audio] Conversion completed successfully: ${outputPath}`);
    
    // Generate a visual waveform array (Instagram expects an array of floats, typically between 0.0 and 1.0)
    // We generate 50 points of variable amplitude to create a beautiful, organic looking audio wave
    const waveform = this.generateWaveform(50);

    return { filePath: outputPath, waveform };
  }

  /**
   * Generates a realistic visual waveform array (normalized 0.0 to 1.0).
   * It uses a sine-wave pattern mixed with random spikes to mimic real speech cadence.
   * @param {number} points - Number of bars in the waveform representation
   * @returns {number[]}
   */
  static generateWaveform(points = 50) {
    const wave = [];
    for (let i = 0; i < points; i++) {
      // Base frequency simulating normal speech dynamics (rises and falls)
      const base = Math.abs(Math.sin((i / points) * Math.PI * 3));
      // Add random spikes and noise
      const noise = Math.random() * 0.3;
      // Combine and scale down slightly
      let amplitude = (base * 0.7) + noise;
      // Clamp between 0.05 and 1.0
      amplitude = Math.max(0.05, Math.min(1.0, amplitude));
      wave.push(parseFloat(amplitude.toFixed(2)));
    }
    return wave;
  }
}

module.exports = AudioProcessor;
