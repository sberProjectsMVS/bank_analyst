import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("../../output/competitor_analysis.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
for (const [sheetId, range] of [
  ["ВТБ", "A1:I49"],
  ["Сводная", "A20:R52"],
  ["Products", "A1:X49"],
]) {
  const table = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    tableMaxRows: 60,
    tableMaxCols: 24,
    tableMaxCellChars: 220,
    maxChars: 30000,
  });
  console.log(table.ndjson);
}
for (const term of ["vtb_prime_5", "vtb_prime_6", "vtb_prime_7", "vtb_prime_8"]) {
  const matches = await workbook.inspect({
    kind: "match",
    searchTerm: term,
    options: { useRegex: false, maxResults: 120 },
    maxChars: 12000,
  });
  console.log(matches.ndjson);
}
