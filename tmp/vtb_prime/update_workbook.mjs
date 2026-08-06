import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import { mkdir, readFile } from "node:fs/promises";

const inputPath = "../../output/competitor_analysis.xlsx";
const comparisonPath = "../../output/comparison_data.json";
const artifactPath = "../../outputs/vtb_prime_sources_2026-08-05/competitor_analysis.xlsx";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const comparison = JSON.parse(await readFile(comparisonPath, "utf8"));
const tierIds = ["vtb_prime_5", "vtb_prime_6", "vtb_prime_7", "vtb_prime_8"];
const fieldIds = ["cashback", "transfers_payments", "cash_withdrawal"];
const rows = new Map(
  comparison.rows
    .filter((row) => tierIds.includes(row.tier_id))
    .map((row) => [row.tier_id, row]),
);

const appendSources = (existing, urls) => {
  const result = String(existing ?? "").trim();
  const missing = urls.filter((url) => !result.includes(url));
  return [result, ...missing].filter(Boolean).join("; ");
};

const commonUrls = [
  "https://private.vtb.ru/bankovskie-uslugi/cashback/",
  "https://private.vtb.ru/bankovskie-uslugi/karty/",
  "https://www.vtb.ru/personal/online-servisy/perevody/",
  "https://h.vtb.ru/projects/tbcv_dgto/files/prime_pictures/vtb_tarif_prime.pdf",
  "https://www.vtb.ru/personal/online-servisy/snyatie-nalichnyh-po-qr/",
];

const vtb = workbook.worksheets.getItem("ВТБ");
const vtbColumns = ["F", "G", "H", "I"];
const vtbFieldRows = { cashback: 12, transfers_payments: 14, cash_withdrawal: 15 };
for (let index = 0; index < tierIds.length; index += 1) {
  const tier = rows.get(tierIds[index]);
  const column = vtbColumns[index];
  for (const fieldId of fieldIds) {
    vtb.getRange(`${column}${vtbFieldRows[fieldId]}`).values = [[tier.fields[fieldId].display_value]];
  }
  vtb.getRange(`${column}3`).values = [["2026-08-05"]];
  const sourceCell = vtb.getRange(`${column}6`);
  sourceCell.values = [[appendSources(sourceCell.values?.[0]?.[0], commonUrls)]];
}

const summary = workbook.worksheets.getItem("Сводная");
const summaryRows = [22, 32, 42, 52];
const summaryColumns = { cashback: "O", transfers_payments: "Q", cash_withdrawal: "R" };
for (let index = 0; index < tierIds.length; index += 1) {
  const tier = rows.get(tierIds[index]);
  for (const fieldId of fieldIds) {
    summary.getRange(`${summaryColumns[fieldId]}${summaryRows[index]}`).values = [[tier.fields[fieldId].display_value]];
  }
}

const products = workbook.worksheets.getItem("Products");
const productRows = [24, 25, 26, 27];
const productColumns = { cashback: "N", cash_withdrawal: "P", transfers_payments: "Q" };
for (let index = 0; index < tierIds.length; index += 1) {
  const tier = rows.get(tierIds[index]);
  for (const fieldId of fieldIds) {
    products.getRange(`${productColumns[fieldId]}${productRows[index]}`).values = [[tier.fields[fieldId].display_value]];
  }
  const sourceCell = products.getRange(`V${productRows[index]}`);
  sourceCell.values = [[appendSources(sourceCell.values?.[0]?.[0], commonUrls)]];
  products.getRange(`W${productRows[index]}`).values = [["2026-08-05"]];
}

const provenance = workbook.worksheets.getItem("Провенанс значений");
const provenanceRows = {
  vtb_prime_5: { cashback: 887, transfers_payments: 889, cash_withdrawal: 890 },
  vtb_prime_6: { cashback: 927, transfers_payments: 929, cash_withdrawal: 930 },
  vtb_prime_7: { cashback: 967, transfers_payments: 969, cash_withdrawal: 970 },
  vtb_prime_8: { cashback: 1007, transfers_payments: 1009, cash_withdrawal: 1010 },
};
const sourceSections = {
  cashback: "Кешбэк; карточный каталог пакета Прайм+",
  transfers_payments: "Лимиты переводов для ПУ «Прайм+»",
  cash_withdrawal: "Раздел 8, пп. 8.1 и 8.3; технический QR-лимит",
};
for (const tierId of tierIds) {
  const tier = rows.get(tierId);
  for (const fieldId of fieldIds) {
    const fact = tier.fields[fieldId];
    const row = provenanceRows[tierId][fieldId];
    provenance.getRange(`G${row}:R${row}`).values = [[
      fact.display_value,
      fact.source_url,
      sourceSections[fieldId],
      fact.source_type,
      fact.date_checked,
      fact.raw_text,
      fact.status,
      fact.conflict_status,
      fact.publication_status,
      fact.publication_reason,
      fact.blocked_value,
      fact.note,
    ]];
  }
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  maxChars: 12000,
});
console.log(errors.ndjson || "NO_FORMULA_ERRORS");

await mkdir("../../outputs/vtb_prime_sources_2026-08-05", { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(artifactPath);
await output.save(inputPath);
console.log(artifactPath);
