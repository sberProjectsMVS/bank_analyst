import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("../../output/competitor_analysis.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
const tiers = new Set(["vtb_prime_5", "vtb_prime_6", "vtb_prime_7", "vtb_prime_8"]);
const fields = new Set(["cashback", "transfers_payments", "cash_withdrawal"]);

const provenance = workbook.worksheets.getItem("Провенанс значений");
const pValues = provenance.getRange("A1:R1939").values;
console.log(JSON.stringify({ provenanceHeader: pValues[0] }));
pValues.forEach((row, index) => {
  if (tiers.has(row[2]) && fields.has(row[4])) {
    console.log(JSON.stringify({
      provenanceRow: index + 1,
      tier: row[2],
      field: row[4],
      value: String(row[6] ?? "").slice(0, 120),
      source: row[7],
      date: row[10],
      reliability: row[12],
      status: row[13],
    }));
  }
});

const products = workbook.worksheets.getItem("Products");
const productValues = products.getRange("A1:X49").values;
console.log(JSON.stringify({ productsHeader: productValues[0] }));
productValues.forEach((row, index) => {
  if (tiers.has(row[1])) {
    console.log(JSON.stringify({
      productRow: index + 1,
      tier: row[1],
      values: row.map((cell) => String(cell ?? "").slice(0, 90)),
    }));
  }
});
