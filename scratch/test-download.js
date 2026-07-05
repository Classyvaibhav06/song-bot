const path = require('path');
const fs = require('fs');

// Ensure modules can be loaded from the relative lib directory
const YouTubeDownloader = require('../lib/youtube');
const AudioProcessor = require('../lib/audio');

const DOWNLOADS_DIR = path.join(__dirname, '../downloads');
const TEST_QUERY = 'synthwave short loop'; // short query to test quickly

async function runTest() {
  console.log('=== Instagram Music Bot: Local Integration Test ===');
  console.log(`Temp Downloads Directory: ${DOWNLOADS_DIR}`);
  console.log(`Test Search Query: "${TEST_QUERY}"`);
  console.log('----------------------------------------------------');

  try {
    // 1. Test YouTube Downloader
    console.log('Step 1: Testing YouTube Search & Download (yt-dlp)...');
    const songInfo = await YouTubeDownloader.downloadSong(TEST_QUERY, DOWNLOADS_DIR);
    console.log('Step 1 Successful! Details:');
    console.log(`- Title: ${songInfo.title}`);
    console.log(`- Video ID: ${songInfo.id}`);
    console.log(`- Local Path: ${songInfo.filePath}`);
    console.log('----------------------------------------------------');

    // 2. Test Audio Processor
    console.log('Step 2: Testing Audio Conversion & Waveform Extraction (ffmpeg)...');
    const audioInfo = await AudioProcessor.convertToVoiceNote(songInfo.filePath, DOWNLOADS_DIR, 30);
    console.log('Step 2 Successful! Details:');
    console.log(`- Voice Note Path: ${audioInfo.filePath}`);
    console.log(`- Waveform Length: ${audioInfo.waveform.length} elements`);
    console.log(`- Waveform Sample (first 10): [ ${audioInfo.waveform.slice(0, 10).join(', ')} ... ]`);
    console.log('----------------------------------------------------');

    // 3. Output status
    console.log('🎉 LOCAL PIPELINE TEST PASSED SUCCESSFULLY!');
    console.log('The YouTube search, yt-dlp downloader, and ffmpeg audio converters are fully functional.');
    console.log(`To clean up test files, delete the "${DOWNLOADS_DIR}" directory.`);
    
  } catch (err) {
    console.error('❌ LOCAL PIPELINE TEST FAILED:', err.message);
    console.log('\nCommon troubleshooting steps:');
    console.log('1. Ensure yt-dlp is installed and in your system PATH.');
    console.log('2. Ensure ffmpeg is installed and in your system PATH.');
    console.log('3. Ensure you have an active internet connection.');
  }
}

// Execute test
runTest();
