import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { exec } from "child_process";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from 'url';
const server = new McpServer({
    name: "synthea-mcp",
    version: "1.0.0"
});
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// The jar is expected to be in the parent medlm directory
const JAR_PATH = path.resolve(__dirname, "../../synthea-with-dependencies.jar");
// The output directory is also in the parent medlm directory
const OUT_DIR = path.resolve(__dirname, "../../output/fhir");
/**
 * Tool: generate_patient_population
 * Generates synthetic patient records using the Synthea Java CLI.
 */
server.tool("generate_patient_population", "Generates synthetic patient records (FHIR R4) using the Synthea Java CLI. Useful for testing applications with realistic healthcare data.", {
    count: z.number().int().min(1).max(100).describe("Number of patients to generate").default(1),
    state: z.string().describe("State to generate patients for (e.g., Massachusetts)").default("Massachusetts")
}, async ({ count, state }) => {
    return new Promise((resolve) => {
        console.error(`[Synthea MCP] Spawning generation for ${count} patients in ${state}...`);
        exec(`java -jar ${JAR_PATH} -p ${count} ${state}`, { cwd: path.resolve(__dirname, "../../") }, (error, stdout, stderr) => {
            if (error) {
                resolve({
                    content: [{ type: "text", text: `Error generating patients: ${error.message}\n${stderr}` }],
                    isError: true
                });
                return;
            }
            resolve({
                content: [
                    { type: "text", text: `Successfully generated ${count} synthetic patients in ${state}.\nOutput logged to ${OUT_DIR}` }
                ]
            });
        });
    });
});
/**
 * Resource: list_patients
 * Allows clients to read the list of generated synthetic JSON files.
 */
server.resource("list_generated_patients", "list://patients", { contentType: "application/json", description: "List all generated synthetic patient FHIR JSON files" }, async (uri) => {
    try {
        const files = await fs.readdir(OUT_DIR);
        const jsonFiles = files.filter(f => f.endsWith('.json') && !f.includes('practitioner') && !f.includes('hospital'));
        return {
            contents: [{
                    uri: uri.href,
                    text: JSON.stringify(jsonFiles, null, 2),
                    mimeType: "application/json"
                }]
        };
    }
    catch (error) {
        return {
            contents: [{
                    uri: uri.href,
                    text: JSON.stringify({ error: "No generated patients found or output directory does not exist." }),
                    mimeType: "application/json"
                }]
        };
    }
});
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Synthea MCP Server started on stdio");
}
main().catch(console.error);
//# sourceMappingURL=index.js.map