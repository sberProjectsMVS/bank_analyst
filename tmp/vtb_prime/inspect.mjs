import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("../../output/competitor_analysis.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 12000,
});
console.log(sheets.ndjson);
const matches = await workbook.inspect({
  kind: "match",
  searchTerm: "Прайм+|Кэшбэк|Кешбэк|Переводы и платежи|Снятие наличных",
  options: { useRegex: true, maxResults: 250 },
  maxChars: 24000,
});
console.log(matches.ndjson);
for (const [sheetId, range] of [
  ["ВТБ", "A1:I49"],
  ["Сводная", "A20:R52"],
  ["Провенанс значений", "A1:R30"],
  ["Products", "A1:X49"],
]) {
  const table = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    tableMaxRows: 60,
    tableMaxCols: 24,
    tableMaxCellChars: 300,
    maxChars: 30000,
  });
  console.log(table.ndjson);
}
