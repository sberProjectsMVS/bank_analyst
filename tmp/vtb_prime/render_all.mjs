import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import { mkdir, writeFile } from "node:fs/promises";

const [inputPath, outputDir] = process.argv.slice(2);
if (!inputPath || !outputDir) throw new Error("usage: render_all.mjs INPUT_XLSX OUTPUT_DIR");

await mkdir(outputDir, { recursive: true });
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheetInfo = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 20000 });
const names = sheetInfo.ndjson
  .trim()
  .split("\n")
  .map((line) => JSON.parse(line))
  .map((entry) => entry.name ?? entry.sheetName)
  .filter(Boolean);

for (let index = 0; index < names.length; index += 1) {
  const name = names[index];
  const safe = String(index + 1).padStart(2, "0") + "_" + name.replaceAll(/[\\/:*?\"<>|]/g, "_");
  try {
    const blob = await workbook.render({ sheetName: name, autoCrop: "all", scale: 0.5, format: "png" });
    await writeFile(`${outputDir}/${safe}.png`, new Uint8Array(await blob.arrayBuffer()));
    console.log(`${index + 1}/${names.length} ${name}`);
  } catch (error) {
    console.error(`FAILED ${index + 1}/${names.length} ${name}: ${error?.message ?? error}`);
  }
}
