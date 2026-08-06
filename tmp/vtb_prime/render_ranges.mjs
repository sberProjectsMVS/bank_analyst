import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import { mkdir, writeFile } from "node:fs/promises";

const input = await FileBlob.load("../../output/competitor_analysis.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
await mkdir("previews_after_ranges", { recursive: true });

const targets = [
  ["Изменения", "A1:Z100", "15_Изменения_top"],
  ["Требует ручной проверки", "A1:I100", "16_Требует_ручной_проверки_top"],
  ["Провенанс значений", "A880:R1015", "18_Провенанс_VTB_Prime"],
  ["Changes", "A1:X100", "23_Changes_top"],
  ["ВТБ", "E1:I16", "05_ВТБ_Prime_detail"],
  ["Products", "A23:X27", "22_Products_VTB_Prime_detail"],
];

for (const [sheetName, range, name] of targets) {
  const blob = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await writeFile(`previews_after_ranges/${name}.png`, new Uint8Array(await blob.arrayBuffer()));
  console.log(`${sheetName} ${range}`);
}
