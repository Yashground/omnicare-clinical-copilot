import fs from 'fs';
import https from 'https';

const SYNTHEA_VERSION = 'v3.3.0'; // Adjust as needed
const JAR_URL = `https://github.com/synthetichealth/synthea/releases/download/${SYNTHEA_VERSION}/synthea-with-dependencies.jar`;
const TARGET_FILE = 'synthea-with-dependencies.jar';

console.log(`Downloading Synthea ${SYNTHEA_VERSION}...`);
console.log(`URL: ${JAR_URL}`);

const file = fs.createWriteStream(TARGET_FILE);

https.get(JAR_URL, (response) => {
    if (response.statusCode === 301 || response.statusCode === 302) {
        // Handle redirect
        https.get(response.headers.location, (redirectResponse) => {
            redirectResponse.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log('✅ Download Complete!');
                console.log(`You can now run Synthea tools from the MCP server.`);
            });
        }).on('error', (err) => {
            fs.unlink(TARGET_FILE, () => {});
            console.error('Error downloading:', err.message);
        });
    } else {
        response.pipe(file);
        file.on('finish', () => {
            file.close();
            console.log('✅ Download Complete!');
        });
    }
}).on('error', (err) => {
    fs.unlink(TARGET_FILE, () => {});
    console.error('Error downloading:', err.message);
});
