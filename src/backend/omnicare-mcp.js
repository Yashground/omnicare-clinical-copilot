import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { exec } from 'child_process';
import { GoogleAuth } from 'google-auth-library';

dotenv.config();

const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/cloud-platform'
});

// Create an MVP Express app for handling traditional HTTP if needed
const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

app.get('/health', (req, res) => {
    res.json({ status: 'OmniCare MCP Server is running' });
});

// Mock state to hold transcripts per encounter
const encounterTranscripts = {};

async function callMedGemma(transcript) {
    const PROJECT_ID = "32142846166";
    const ENDPOINT_ID = "mg-endpoint-6a2cdec4-6429-4edc-a0b4-6081749e0696";
    const LOCATION = "europe-west4";
    const HOST = "mg-endpoint-6a2cdec4-6429-4edc-a0b4-6081749e0696.europe-west4-32142846166.prediction.vertexai.goog";
    const url = `https://${HOST}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/endpoints/${ENDPOINT_ID}:predict`;

    try {
        const client = await auth.getClient();
        const token = await client.getAccessToken();

        const payload = {
            "instances": [
                {
                    "@requestFormat": "chatCompletions",
                    "messages": [
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": "You are an expert clinical AI assistant. Generate a structured SOAP (Subjective, Objective, Assessment, Plan) note based on the provided clinical encounter transcript."}]
                        },
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": `Transcript: ${transcript}\n\nGenerate structured SOAP Note:`}]
                        }
                    ],
                    "max_tokens": 1024
                }
            ]
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error("MedGemma Error Status:", response.status);
            const errorText = await response.text();
            console.error("MedGemma Error Body:", errorText);
            return `[API Error] Status: ${response.statusText}`;
        }

        const data = await response.json();
        // Extract the generated chat response text
        if (data.predictions && data.predictions.choices && data.predictions.choices[0]) {
            return data.predictions.choices[0].message.content;
        } else if (data.predictions && data.predictions[0] && data.predictions[0].choices) {
            return data.predictions[0].choices[0].message.content;
        } else if (data.choices && data.choices[0] && data.choices[0].message) {
            return data.choices[0].message.content;
        }
        return JSON.stringify(data);

    } catch (error) {
        console.error("Exception calling MedGemma:", error);
        return `[Exception] ${error.message}`;
    }
}

async function callMedASR(audioBase64) {
    const PROJECT_ID = "32142846166";
    const ENDPOINT_ID = "mg-endpoint-d6a4a403-d834-4a85-ba9c-439648042ba0";
    const LOCATION = "europe-west1";
    const HOST = "mg-endpoint-d6a4a403-d834-4a85-ba9c-439648042ba0.europe-west1-779153331066.prediction.vertexai.goog";
    const url = `https://${HOST}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/endpoints/${ENDPOINT_ID}:predict`;
    
    console.log(`[MedASR] Forwarding audio chunk to Vertex AI endpoint...`);
    try {
        const client = await auth.getClient();
        const token = await client.getAccessToken();

        // Vertex AI :predict endpoints usually require instances array.
        // However, MedASR model expects the payload directly without instances wrapper!
        const payload = {
            "file": audioBase64
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error("MedASR Error Status:", response.status);
            const errorText = await response.text();
            console.error("MedASR Error Body:", errorText);
            return `[API Error] Status: ${response.statusText}`;
        }

        const data = await response.json();
        
        // Extract transcription depending on how the model formats it
        if (data.predictions && data.predictions[0]) {
             if (typeof data.predictions[0] === 'string') return data.predictions[0];
             if (data.predictions[0].text) return data.predictions[0].text;
             if (data.predictions[0].transcript) return data.predictions[0].transcript;
        }
        
        if (data.text) {
            return data.text;
        }
        
        return JSON.stringify(data);

    } catch (error) {
        console.error("Exception calling MedASR:", error);
        return `[Exception] ${error.message}`;
    }
}

app.post('/api/transcribe', async (req, res) => {
    const { encounter_id, text_chunk, audio_chunk } = req.body;
    
    if (!encounterTranscripts[encounter_id]) {
        encounterTranscripts[encounter_id] = "";
    }
    
    let current_text = text_chunk;

    // If audio was sent instead of text, process via MedASR
    if (audio_chunk) {
        current_text = await callMedASR(audio_chunk);
    }
    
    // Ensure we have a fresh state for this encounter if it's the first time we see it
    if (!encounterTranscripts[encounter_id]) {
        console.log(`[OmniCare] Initializing fresh state for encounter: ${encounter_id}`);
        encounterTranscripts[encounter_id] = "";
    }
    
    // Append the new text
    if (current_text) {
        encounterTranscripts[encounter_id] += " " + current_text;
    }
    
    const chunkCount = encounterTranscripts[encounter_id].split('.').length;
    
    let soap_note = null;
    // We'll trigger a real SOAP note via MedGemma every ~3 chunks/sentences for demonstration
    if (chunkCount > 3) {
        console.log(`[OmniCare] Triggering MedGemma SOAP generation for ${encounter_id}...`);
        soap_note = await callMedGemma(encounterTranscripts[encounter_id].trim());
    }
    
    res.json({
        success: true,
        current_transcript: encounterTranscripts[encounter_id],
        soap_note: soap_note
    });
});

// New Endpoint: Option C FHIR Vitals Wrapper
app.post('/api/fhir/observation', (req, res) => {
    const observation = req.body;
    
    // Log the incoming vital sign
    if (observation && observation.resourceType === 'Observation') {
        const type = observation.code?.coding?.[0]?.display || "Unknown Vital";
        const value = observation.valueQuantity ? `${observation.valueQuantity.value} ${observation.valueQuantity.unit}` : "N/A";
        console.log(`[FHIR STREAM] Received ${type}: ${value}`);
        
        // INTEGRATION STUB: Google Cloud Healthcare API
        // fhirStore.executeBundle(...) -> Pushes to real GCP FHIR Store
    }

    res.json({ success: true, message: 'Observation received and logged.' });
});

// Initialize MCP Server
const server = new McpServer({
    name: "omnicare-mcp",
    version: "1.0.0"
});

// Example Tool: Generate Synthetic Data using Synthea CLI
server.tool(
    "generate_synthea_data",
    "Generates synthetic patient data using the Synthea CLI",
    {
        patientCount: z.number().describe("Number of patients to generate").default(1),
        state: z.string().describe("State to generate patients for").default("Massachusetts")
    },
    async ({ patientCount, state }) => {
        return new Promise((resolve) => {
            console.log(`[MCP] Executing Synthea generation for ${patientCount} patients in ${state}...`);
            // Execute the synthea java binary (requires setup_synthea.js to download it first)
            exec(`java -jar synthea-with-dependencies.jar -p ${patientCount} ${state}`, (error, stdout, stderr) => {
                if (error) {
                    console.error(`Synthea Error: ${error.message}`);
                    resolve({
                        content: [{ type: "text", text: `Error generating patients: ${error.message}` }]
                    });
                    return;
                }
                resolve({
                    content: [{ type: "text", text: `Successfully generated ${patientCount} synthetic patients in ${state}.\nOutput logged to ./output/fhir/` }]
                });
            });
        });
    }
);

import { fileURLToPath } from 'url';

// Start the Express Server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Express Mock Backend running on port ${PORT}`);
});

// Start the MCP Server via stdio
async function run() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.log("OmniCare MCP Server started via stdio.");
}

// Only run MCP server if executed directly (not imported)
const __filename_esm = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename_esm) {
    run().catch(console.error);
}

// Export for potential external usage
export { app, server };
