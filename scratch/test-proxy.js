const { HttpsProxyAgent } = require('https-proxy-agent');
const https = require('https');

const WEBSHARE_PROXY = {
  host: 'p.webshare.io',
  port: 6754,
  username: 'bwqinulg',
  password: 'gfahji58r2kk',
  get url() {
    return `http://${this.username}:${this.password}@${this.host}:${this.port}`;
  }
};

console.log(`Connecting to proxy: ${WEBSHARE_PROXY.host}:${WEBSHARE_PROXY.port}...`);

try {
  const agent = new HttpsProxyAgent(WEBSHARE_PROXY.url);
  
  const req = https.get('https://api.ipify.org?format=json', { agent }, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
      console.log('✅ Proxy Connection Successful!');
      console.log('Response:', data);
    });
  });

  req.on('error', (err) => {
    console.error('❌ Proxy Request Failed:', err.message);
    console.error('Error Details:', err);
  });
} catch (e) {
  console.error('❌ Direct Exception:', e.message);
}
