import fs from 'fs';
import { GoogleAuth } from 'google-auth-library';

async function getToken() {
  const auth = new GoogleAuth({ scopes: 'https://www.googleapis.com/auth/cloud-platform' });
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  fs.writeFileSync('token.txt', token.token);
  console.log('Saved token to token.txt');
}
getToken().catch(console.error);
