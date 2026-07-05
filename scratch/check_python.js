const { exec } = require('child_process');
exec('python --version', (err, stdout, stderr) => {
  if (err) {
    console.error('Error executing python:', err.message);
    console.error('stderr:', stderr);
    return;
  }
  console.log('stdout:', stdout);
});
