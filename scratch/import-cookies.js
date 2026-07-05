const fs = require('fs');
const path = require('path');
const { IgApiClient } = require('instagram-private-api');
const Chance = require('chance');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const username = config.instagram.username;
const sessionPath = path.join(__dirname, '../session.json');

const readline = require('readline');
function askQuestion(query) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => rl.question(query, ans => { rl.close(); resolve(ans.trim()); }));
}

(async () => {
  console.log('================================================================');
  console.log('🍪 INSTAGRAM COOKIE IMPORT TOOL');
  console.log('================================================================');
  console.log('Follow these steps to extract your session ID:');
  console.log('1. Open your browser and go to https://www.instagram.com');
  console.log('2. Log in as "vot.music" if you aren\'t already.');
  console.log('3. Press F12 (or right-click -> Inspect) to open DevTools.');
  console.log('4. Go to the "Application" tab (Chrome/Edge) or "Storage" tab (Firefox).');
  console.log('5. Under "Storage" in the left sidebar, expand "Cookies" and click "https://www.instagram.com".');
  console.log('6. Look for the cookie named "sessionid" and copy its Value.');
  console.log('================================================================\n');

  const sessionId = await askQuestion('🔑 Paste the value of your "sessionid" cookie: ');
  if (!sessionId) {
    console.error('Error: sessionid cannot be empty.');
    process.exit(1);
  }

  const dsUserId = await askQuestion('🔑 Paste the value of your "ds_user_id" cookie (optional, press Enter to auto-extract): ');
  
  // Extract user ID from sessionid if not provided (it is usually the prefix of the sessionid before the first split)
  let userId = dsUserId;
  if (!userId) {
    const parts = sessionId.split('%');
    if (parts.length > 0 && /^\d+$/.test(parts[0])) {
      userId = parts[0];
    } else {
      userId = await askQuestion('🔑 Enter your numeric Instagram User ID (e.g. 6428139581): ');
    }
  }

  if (!userId) {
    console.error('Error: Could not determine User ID.');
    process.exit(1);
  }

  const csrfToken = await askQuestion('🔑 Paste the value of your "csrftoken" cookie (optional, press Enter to generate dummy): ') || 'missing_token';

  console.log('\n================================================================');
  console.log('🌐 EXTRACT YOUR BROWSER\'S USER-AGENT');
  console.log('================================================================');
  console.log('1. In your browser DevTools, click the "Console" tab.');
  console.log('2. Type this command and press Enter:');
  console.log('   navigator.userAgent');
  console.log('3. Copy the returned string (without quotes) and paste it below.');
  console.log('================================================================\n');

  const userAgent = await askQuestion('🔑 Paste your browser\'s User-Agent: ');
  if (!userAgent) {
    console.error('Error: User-Agent cannot be empty.');
    process.exit(1);
  }

  // Build the tough-cookie serialized structure
  const now = new Date().toISOString();
  const serializedCookies = {
    version: 'tough-cookie@4.1.3',
    storeType: 'MemoryCookieStore',
    // ... rest same
  };

  // Generate deterministic device identifiers
  const chance = new Chance(username);
  const id = chance.string({ pool: 'abcdef0123456789', length: 16 });
  const deviceState = {
    deviceString: chance.pickone([
      'Android (29/10; 1080x2280; OnePlus; ONEPLUS A6013; OnePlus6T; qcom; en_US; 319.0.0.39.117)',
      'Android (29/10; 1080x2340; Xiaomi; Redmi Note 8 Pro; begonia; qcom; en_US; 319.0.0.39.117)'
    ]),
    deviceId: `android-${id}`,
    uuid: chance.guid(),
    phoneId: chance.guid(),
    adid: chance.guid(),
    cookieUserId: userId,
    cookieUserName: username,
    userAgent: userAgent,
    cookies: JSON.stringify({
      version: 'tough-cookie@4.1.3',
      storeType: 'MemoryCookieStore',
      rejectPublicSuffixes: true,
      enableLooseMode: false,
      cookies: [
        {
          key: 'sessionid',
          value: sessionId,
          domain: 'instagram.com',
          path: '/',
          secure: true,
          httpOnly: true,
          hostOnly: false,
          creation: now,
          lastAccessed: now
        },
        {
          key: 'ds_user_id',
          value: userId,
          domain: 'instagram.com',
          path: '/',
          secure: true,
          hostOnly: false,
          creation: now,
          lastAccessed: now
        },
        {
          key: 'csrftoken',
          value: csrfToken,
          domain: 'instagram.com',
          path: '/',
          secure: true,
          hostOnly: false,
          creation: now,
          lastAccessed: now
        }
      ]
    })
  };

  fs.writeFileSync(sessionPath, JSON.stringify(deviceState, null, 2), 'utf8');
  console.log(`\n🎉 SUCCESS! Fully authenticated session written to ${sessionPath}`);
  console.log('You can now run "npm start" to run your bot immediately!');
})();
