require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { IgApiClient } = require('instagram-private-api');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const username = process.env.IG_USERNAME || config.instagram.username;
const password = process.env.IG_PASSWORD || config.instagram.password;
const sessionPath = path.join(__dirname, '../session.json');
const musicSearchDocId = config.instagram.musicSearchDocId || '27152225807728809';

const client = new IgApiClient();

client.state.constants.APP_VERSION = '319.0.0.39.117';
client.state.constants.APP_VERSION_CODE = '555431602';
client.state.constants.FACEBOOK_ANALYTICS_APPLICATION_ID = '252386858233363';
client.state.constants.FACEBOOK_ORCA_APPLICATION_ID = '1178275498895048';

async function saveSession() {
  const cookies = await client.state.serializeCookieJar();
  const state = {
    deviceString: client.state.deviceString,
    deviceId: client.state.deviceId,
    uuid: client.state.uuid,
    phoneId: client.state.phoneId,
    adid: client.state.adid,
    cookies: JSON.stringify(cookies)
  };
  fs.writeFileSync(sessionPath, JSON.stringify(state, null, 2), 'utf8');
  console.log(`[Session] Saved to ${sessionPath}`);
}

async function loadSession() {
  if (!fs.existsSync(sessionPath)) return false;
  try {
    const state = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
    client.state.deviceString = state.deviceString;
    client.state.deviceId = state.deviceId;
    client.state.uuid = state.uuid;
    client.state.phoneId = state.phoneId;
    client.state.adid = state.adid;
    if (state.userAgent) {
      Object.defineProperty(client.state, 'appUserAgent', {
        get: () => state.userAgent,
        configurable: true
      });
    }
    await client.state.deserializeCookieJar(JSON.parse(state.cookies));
    console.log(`[Session] Loaded successfully.`);
    return true;
  } catch (err) {
    console.warn(`[Session] Failed to load:`, err.message);
    return false;
  }
}

const readline = require('readline');
function askQuestion(query) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => rl.question(query, ans => { rl.close(); resolve(ans.trim()); }));
}

const { HttpsProxyAgent } = require('https-proxy-agent');

const WEBSHARE_PROXY = {
  enabled: false, // Disabled proxy to connect directly from home IP
  host: '31.59.20.176',
  port: 6754,
  username: 'bwqinulg',
  password: 'gfahji58r2kk',
  get url() {
    return `http://${this.username}:${this.password}@${this.host}:${this.port}`;
  }
};

async function handleChallenge() {
  console.log('[Auth] Initiating automatic challenge resolution...');
  try {
    const challengeResult = await client.challenge.auto(false);
    console.log('[Auth] Challenge auto result:', JSON.stringify(challengeResult, null, 2));
    console.log(`[Auth] Challenge method: ${challengeResult.step_name || 'unknown'}`);
    
    const code = await askQuestion('🔑 Enter the 6-digit verification code sent to your email/SMS: ');
    if (!code || !/^\d{6}$/.test(code)) {
      throw new Error('Invalid verification code format. Must be 6 digits.');
    }
    
    console.log('[Auth] Submitting verification code...');
    const challengeState = await client.challenge.sendSecurityCode(code);
    console.log(`[Auth] Challenge resolved! Status: ${challengeState.status || 'OK'}`);
    return true;
  } catch (err) {
    console.error('[Auth] Challenge auto() threw an error:', err.message);
    if (err.response && err.response.body) {
      console.error('[Auth] Challenge error response body:', JSON.stringify(err.response.body, null, 2));
    }
    if (err.message && (err.message.includes('already approved') || (err.response?.body?.step_name === 'finish'))) {
      console.log('[Auth] Challenge appears to be manually approved.');
      return true;
    }
    console.error('[Auth] Challenge resolution failed.');
    throw err;
  }
}

async function authenticate() {
  console.log('[Auth] Checking session...');
  
  if (WEBSHARE_PROXY.enabled) {
    try {
      const proxyAgent = new HttpsProxyAgent(WEBSHARE_PROXY.url);
      client.request.defaults.agent = proxyAgent;
      console.log(`[Proxy] ✅ Webshare active: ${WEBSHARE_PROXY.host}:${WEBSHARE_PROXY.port}`);
    } catch (proxyErr) {
      console.error(`[Proxy] ❌ Error:`, proxyErr.message);
    }
  }

  const isLoaded = await loadSession();
  if (isLoaded) {
    console.log('[Auth] Session loaded from file. Skipping mobile verification check...');
    return;
  }

  console.log('[Auth] Performing fresh login...');
  client.state.generateDevice(username);
  await client.simulate.preLoginFlow();
  
  try {
    await client.account.login(username, password);
    console.log('[Auth] Logged in successfully!');
    await saveSession();
  } catch (err) {
    const isCheckpoint = err.name === 'IgCheckpointError' || 
                         (err.message && err.message.includes('challenge_required')) ||
                         (err.response && err.response.body && err.response.body.error_type === 'checkpoint_challenge_required');
    
    if (isCheckpoint) {
      console.log('[Auth] Checkpoint required.');
      
      if (err.response && err.response.body) {
        client.state.checkpoint = err.response.body;
      }
      
      let challengeResolved = false;
      try {
        challengeResolved = await handleChallenge();
      } catch (autoErr) {
        console.log('[Auth] Auto challenge failed, retrying manual console prompt...');
      }
      
      if (!challengeResolved) {
        let challengeUrl = err.response?.body?.challenge?.url || 'https://instagram.com/challenge/';
        challengeUrl = challengeUrl.replace('i.instagram.com', 'instagram.com');
        
        console.log('\n================================================================');
        console.log('⚠️  Instagram Checkpoint (Fallback):');
        console.log(`   URL: ${challengeUrl}`);
        console.log('   F12 (Mobile Emulation) -> Approve');
        console.log('================================================================\n');
        
        await askQuestion('Press ENTER after you have approved the checkpoint in your browser...');
        try { await client.challenge.state(); challengeResolved = true; } catch (e) {}
      }
      
      try {
        const currentUser = await client.account.currentUser();
        console.log(`[Auth] Logged in successfully! Username: ${currentUser.username}`);
        await saveSession();
      } catch (verifyErr) {
        console.log('[Auth] Session verification failed, retrying login...');
        await client.account.login(username, password);
        console.log('[Auth] Logged in successfully!');
        await saveSession();
      }
    } else {
      throw err;
    }
  }
}

async function testSearch(query) {
  console.log(`[Test] Searching for "${query}" via GraphQL...`);
  try {
    const response = await client.request.send({
      url: '/api/v1/ads/graphql/',
      method: 'POST',
      form: {
        doc_id: musicSearchDocId,
        variables: JSON.stringify({ query, count: 5 })
      }
    });
    console.log('[Test] Response status:', response.status);
    console.log('[Test] Response body data keys:', Object.keys(response.body?.data || {}));
    console.log('[Test] Full Response Body:', JSON.stringify(response.body, null, 2));
  } catch (err) {
    const isCheckpoint = err.name === 'IgCheckpointError' || 
                         (err.message && err.message.includes('challenge_required')) ||
                         (err.response && err.response.body && err.response.body.error_type === 'checkpoint_challenge_required');
    
    if (isCheckpoint) {
      console.log(`[Test] Checkpoint required for search endpoint.`);
      let challengeUrl = 'https://www.instagram.com/challenge/';
      try {
        if (err.response && err.response.body && err.response.body.challenge && err.response.body.challenge.url) {
          challengeUrl = err.response.body.challenge.url;
        }
      } catch (e) {}
      
      challengeUrl = challengeUrl.replace('i.instagram.com', 'instagram.com');
      
      console.log('\n================================================================');
      console.log('⚠️  Instagram needs approval for the search action!');
      console.log('1. Open this URL in your web browser:');
      console.log(`   ${challengeUrl}`);
      console.log('2. VERY IMPORTANT: Press F12 (Inspect), click the Mobile Device icon');
      console.log('   to emulate a mobile phone, and reload the page to load it.');
      console.log('3. Complete the verification prompts on that page.');
      console.log('4. Once completed, come back here and press ENTER.');
      console.log('================================================================\n');
      
      await askQuestion('Press ENTER after you have approved the checkpoint in your browser...');
      
      console.log('[Test] Retrying search...');
      try {
        const response = await client.request.send({
          url: '/api/v1/ads/graphql/',
          method: 'POST',
          form: {
            doc_id: musicSearchDocId,
            variables: JSON.stringify({ query, count: 5 })
          }
        });
        console.log('[Test] Retry Response status:', response.status);
        console.log('[Test] Retry Full Response Body:', JSON.stringify(response.body, null, 2));
      } catch (retryErr) {
        console.error('[Test] Retry failed:', retryErr.message);
        if (retryErr.response && retryErr.response.body) {
          console.error('[Test] Retry error response body:', JSON.stringify(retryErr.response.body, null, 2));
        }
      }
    } else {
      console.error('[Test] Search request failed:', err.message);
    }
  }
}

(async () => {
  try {
    await authenticate();
    await testSearch('Shape of You');
  } catch (err) {
    console.error('Fatal Test Error:', err.message);
  }
})();
